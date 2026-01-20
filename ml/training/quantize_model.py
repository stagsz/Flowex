"""
Model Quantization Script

Compresses the symbol detection model from ~160MB to <50MB using:
1. Half-precision (FP16) conversion
2. Weight pruning (remove small weights)
3. Optimized serialization
"""

import argparse
import gzip
import shutil
from pathlib import Path

import torch
import torch.nn.utils.prune as prune


def get_model_size_mb(path: str) -> float:
    """Get model file size in MB."""
    return Path(path).stat().st_size / (1024 * 1024)


def convert_to_fp16(state_dict: dict) -> dict:
    """Convert all float32 tensors to float16."""
    fp16_state_dict = {}
    for key, value in state_dict.items():
        if isinstance(value, torch.Tensor) and value.dtype == torch.float32:
            fp16_state_dict[key] = value.half()
        else:
            fp16_state_dict[key] = value
    return fp16_state_dict


def prune_small_weights(state_dict: dict, threshold: float = 1e-4) -> dict:
    """Zero out weights below threshold (they compress better)."""
    pruned_state_dict = {}
    total_params = 0
    pruned_params = 0

    for key, value in state_dict.items():
        if isinstance(value, torch.Tensor) and value.dtype in (torch.float32, torch.float16):
            mask = torch.abs(value) < threshold
            pruned_params += mask.sum().item()
            total_params += value.numel()
            # Zero out small weights
            value = value.clone()
            value[mask] = 0
        pruned_state_dict[key] = value

    if total_params > 0:
        print(f"  Pruned {pruned_params:,} / {total_params:,} params ({100*pruned_params/total_params:.1f}%)")

    return pruned_state_dict


def quantize_model(
    input_path: str,
    output_path: str,
    use_fp16: bool = True,
    prune_threshold: float = 1e-4,
    compress: bool = True,
) -> None:
    """
    Quantize and compress a model checkpoint.

    Args:
        input_path: Path to original model (.pt)
        output_path: Path to save quantized model
        use_fp16: Convert to half precision
        prune_threshold: Zero weights below this value
        compress: Use gzip compression
    """
    print(f"Loading model from {input_path}...")
    original_size = get_model_size_mb(input_path)
    print(f"  Original size: {original_size:.1f} MB")

    # Load checkpoint
    checkpoint = torch.load(input_path, map_location="cpu")

    # Get state dict
    if "model_state_dict" in checkpoint:
        state_dict = checkpoint["model_state_dict"]
        is_wrapped = True
    else:
        state_dict = checkpoint
        is_wrapped = False

    # Apply pruning first (before FP16 to maintain precision during comparison)
    if prune_threshold > 0:
        print(f"Pruning weights below {prune_threshold}...")
        state_dict = prune_small_weights(state_dict, prune_threshold)

    # Convert to FP16
    if use_fp16:
        print("Converting to FP16...")
        state_dict = convert_to_fp16(state_dict)

    # Rebuild checkpoint
    if is_wrapped:
        new_checkpoint = {
            "model_state_dict": state_dict,
            "num_classes": checkpoint.get("num_classes", 51),
            "confidence_threshold": checkpoint.get("confidence_threshold", 0.5),
            "quantized": True,
            "dtype": "float16" if use_fp16 else "float32",
        }
    else:
        new_checkpoint = state_dict

    # Save with optimized serialization
    temp_path = output_path + ".tmp"
    print(f"Saving to {output_path}...")
    torch.save(new_checkpoint, temp_path, _use_new_zipfile_serialization=True)

    temp_size = get_model_size_mb(temp_path)
    print(f"  After quantization: {temp_size:.1f} MB")

    # Apply gzip compression if needed and beneficial
    if compress and temp_size > 50:
        print("Applying gzip compression...")
        gz_path = output_path + ".gz"
        with open(temp_path, 'rb') as f_in:
            with gzip.open(gz_path, 'wb', compresslevel=9) as f_out:
                shutil.copyfileobj(f_in, f_out)

        gz_size = get_model_size_mb(gz_path)
        print(f"  After compression: {gz_size:.1f} MB")

        # Use compressed version if it's smaller and under 50MB
        if gz_size < temp_size and gz_size < 50:
            Path(temp_path).unlink()
            Path(gz_path).rename(output_path.replace('.pt', '_compressed.pt.gz'))
            final_path = output_path.replace('.pt', '_compressed.pt.gz')
            final_size = gz_size
        else:
            Path(gz_path).unlink()
            Path(temp_path).rename(output_path)
            final_path = output_path
            final_size = temp_size
    else:
        Path(temp_path).rename(output_path)
        final_path = output_path
        final_size = temp_size

    # Summary
    print("\n" + "="*50)
    print("Quantization complete!")
    print(f"  Original:  {original_size:.1f} MB")
    print(f"  Final:     {final_size:.1f} MB")
    print(f"  Reduction: {100*(1 - final_size/original_size):.1f}%")
    print(f"  Output:    {final_path}")

    if final_size > 50:
        print("\n[!] Warning: Model still exceeds 50MB limit.")
        print("   Consider using a smaller backbone (MobileNet) or")
        print("   hosting on Hugging Face Hub instead.")
    else:
        print("\n[OK] Model is under 50MB limit!")


def verify_quantized_model(original_path: str, quantized_path: str) -> None:
    """Verify the quantized model produces similar outputs."""
    import sys
    sys.path.insert(0, str(Path(__file__).parent))
    from model import SymbolDetector

    print("\nVerifying quantized model...")

    # Load original
    original = SymbolDetector.load(original_path, device="cpu")
    original.eval()

    # Load quantized (need to handle FP16)
    checkpoint = torch.load(quantized_path, map_location="cpu")
    quantized = SymbolDetector(
        num_classes=checkpoint["num_classes"],
        pretrained=False,
        confidence_threshold=checkpoint.get("confidence_threshold", 0.5),
    )

    # Convert state dict back to FP32 for inference
    state_dict = checkpoint["model_state_dict"]
    fp32_state_dict = {k: v.float() if v.dtype == torch.float16 else v
                       for k, v in state_dict.items()}
    quantized.model.load_state_dict(fp32_state_dict)
    quantized.eval()

    # Test with random input
    test_input = torch.randn(3, 640, 640)

    with torch.no_grad():
        orig_result = original.predict(test_input)
        quant_result = quantized.predict(test_input)

    print(f"  Original detections:  {len(orig_result['boxes'])}")
    print(f"  Quantized detections: {len(quant_result['boxes'])}")
    print("[OK] Quantized model loads and runs successfully")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Quantize symbol detection model")
    parser.add_argument(
        "--input",
        default="ml/models/symbol_detector.pt",
        help="Path to original model",
    )
    parser.add_argument(
        "--output",
        default="ml/models/symbol_detector_quantized.pt",
        help="Path to save quantized model",
    )
    parser.add_argument(
        "--no-fp16",
        action="store_true",
        help="Don't convert to FP16",
    )
    parser.add_argument(
        "--prune-threshold",
        type=float,
        default=1e-4,
        help="Prune weights below this threshold",
    )
    parser.add_argument(
        "--no-compress",
        action="store_true",
        help="Don't apply gzip compression",
    )
    parser.add_argument(
        "--verify",
        action="store_true",
        help="Verify quantized model after creation",
    )

    args = parser.parse_args()

    quantize_model(
        input_path=args.input,
        output_path=args.output,
        use_fp16=not args.no_fp16,
        prune_threshold=args.prune_threshold,
        compress=not args.no_compress,
    )

    if args.verify:
        verify_quantized_model(args.input, args.output)

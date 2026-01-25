"""
Quick validation test for the ML model.
Tests model loading, forward pass, and basic inference.
"""

import sys
from pathlib import Path

# Add training directory to path
sys.path.insert(0, str(Path(__file__).parent / "training"))

import torch


def test_model_loading():
    """Test that the saved model can be loaded."""
    model_path = Path(__file__).parent / "models" / "best_model.pt"
    if not model_path.exists():
        print(f"SKIP: Model file not found at {model_path}")
        return True

    # Check checkpoint to determine model type
    checkpoint = torch.load(model_path, map_location="cpu", weights_only=False)
    backbone_name = checkpoint.get("backbone_name", "resnet50")
    num_classes = checkpoint.get("num_classes", 51)

    print(f"  Checkpoint: backbone={backbone_name}, num_classes={num_classes}")

    # Use appropriate model class based on backbone
    if backbone_name in ["mobilenet_v3_small", "mobilenet_v3_large"]:
        from model_mobile import MobileSymbolDetector
        model = MobileSymbolDetector.load(str(model_path))
    else:
        from model import SymbolDetector
        model = SymbolDetector.load(str(model_path))

    print(f"OK: Model loaded successfully from {model_path}")
    return True


def test_forward_pass():
    """Test that the model can perform a forward pass."""
    from model import SymbolDetector

    # Create a small model for testing
    model = SymbolDetector(num_classes=51, pretrained=False)
    model.eval()

    # Create dummy input (single image, 3 channels, 800x800)
    dummy_input = torch.randn(3, 800, 800)

    # Run inference - predict takes a single tensor
    with torch.no_grad():
        result = model.predict(dummy_input)

    assert "boxes" in result, "Missing 'boxes' in result"
    assert "labels" in result, "Missing 'labels' in result"
    assert "scores" in result, "Missing 'scores' in result"

    print(f"OK: Forward pass completed - {len(result['boxes'])} detections")
    return True


def test_dataset_loading():
    """Test that the dataset class works."""
    from dataset import PIDDataset, get_val_transforms

    data_path = Path(__file__).parent / "data" / "synthetic"
    if not data_path.exists():
        print(f"SKIP: Dataset not found at {data_path}")
        return True

    dataset = PIDDataset(str(data_path), transforms=get_val_transforms())
    print(f"OK: Dataset loaded with {len(dataset)} samples and {len(dataset.categories)} categories")

    if len(dataset) > 0:
        # Test loading a sample
        image, target = dataset[0]
        assert isinstance(image, torch.Tensor), "Image should be a tensor"
        assert "boxes" in target, "Target should have boxes"
        assert "labels" in target, "Target should have labels"
        print(f"OK: Sample loaded - image shape: {image.shape}")

    return True


def test_mobile_model():
    """Test the mobile model variant."""
    from model_mobile import MobileSymbolDetector

    model = MobileSymbolDetector(
        num_classes=51,
        backbone="mobilenet_v3_small",
        pretrained=False
    )
    model.eval()

    # predict takes a single tensor, not a list
    dummy_input = torch.randn(3, 640, 640)

    with torch.no_grad():
        result = model.predict(dummy_input)

    assert "boxes" in result
    print(f"OK: Mobile model forward pass completed - {len(result['boxes'])} detections")
    return True


def main():
    """Run all tests."""
    print("=" * 60)
    print("P&ID Symbol Detection Model Tests")
    print("=" * 60)

    tests = [
        ("Model Loading", test_model_loading),
        ("Forward Pass", test_forward_pass),
        ("Dataset Loading", test_dataset_loading),
        ("Mobile Model", test_mobile_model),
    ]

    passed = 0
    failed = 0

    for name, test_fn in tests:
        print(f"\n[{name}]")
        try:
            if test_fn():
                passed += 1
        except Exception as e:
            print(f"FAIL: {e}")
            failed += 1

    print("\n" + "=" * 60)
    print(f"Results: {passed} passed, {failed} failed")
    print("=" * 60)

    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())

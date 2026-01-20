"""
P&ID Symbol Detection Training Script

Trains a Faster R-CNN model on synthetic P&ID data.
"""

import argparse
import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path

import torch
from torch.utils.data import DataLoader, random_split

from dataset import PIDDataset, collate_fn, get_train_transforms, get_val_transforms
from model import SymbolDetector
from model_mobile import MobileSymbolDetector

# Default to 50 ISO classes, but can be overridden for other datasets
NUM_CLASSES = 50


def train_one_epoch(
    model: torch.nn.Module,
    optimizer: torch.optim.Optimizer,
    data_loader: DataLoader,
    device: torch.device,
    epoch: int,
    print_freq: int = 10,
) -> dict:
    """Train for one epoch."""
    model.train()

    total_loss = 0.0
    num_batches = 0

    for batch_idx, (images, targets) in enumerate(data_loader):
        # Move to device
        images = [img.to(device) for img in images]
        targets = [{k: v.to(device) for k, v in t.items()} for t in targets]

        # Forward pass
        loss_dict = model(images, targets)
        losses = sum(loss for loss in loss_dict.values())

        # Backward pass
        optimizer.zero_grad()
        losses.backward()
        optimizer.step()

        total_loss += losses.item()
        num_batches += 1

        if (batch_idx + 1) % print_freq == 0:
            avg_loss = total_loss / num_batches
            print(f"  Epoch {epoch} [{batch_idx + 1}/{len(data_loader)}] Loss: {avg_loss:.4f}")

    return {"loss": total_loss / num_batches}


@torch.no_grad()
def evaluate(
    model: torch.nn.Module,
    data_loader: DataLoader,
    device: torch.device,
) -> dict:
    """Evaluate model on validation set."""
    model.eval()

    total_loss = 0.0
    num_batches = 0

    for images, targets in data_loader:
        images = [img.to(device) for img in images]
        targets = [{k: v.to(device) for k, v in t.items()} for t in targets]

        # Get loss in eval mode
        model.train()  # Temporarily set to train to get loss
        loss_dict = model(images, targets)
        losses = sum(loss for loss in loss_dict.values())
        model.eval()

        total_loss += losses.item()
        num_batches += 1

    return {"val_loss": total_loss / num_batches}


def save_checkpoint(
    model: SymbolDetector | MobileSymbolDetector,
    optimizer: torch.optim.Optimizer,
    epoch: int,
    metrics: dict,
    path: str,
) -> None:
    """Save training checkpoint."""
    checkpoint = {
        "epoch": epoch,
        "model_state_dict": model.model.state_dict(),
        "optimizer_state_dict": optimizer.state_dict(),
        "num_classes": model.num_classes,
        "confidence_threshold": model.confidence_threshold,
        "metrics": metrics,
    }
    # Add backbone info for MobileSymbolDetector
    if hasattr(model, "backbone_name"):
        checkpoint["backbone_name"] = model.backbone_name
    torch.save(checkpoint, path)


def load_checkpoint(
    path: str,
    model: SymbolDetector | MobileSymbolDetector,
    optimizer: torch.optim.Optimizer | None = None,
) -> int:
    """Load checkpoint and return epoch number."""
    checkpoint = torch.load(path, map_location="cpu", weights_only=False)
    model.model.load_state_dict(checkpoint["model_state_dict"])
    if optimizer and "optimizer_state_dict" in checkpoint:
        optimizer.load_state_dict(checkpoint["optimizer_state_dict"])
    return checkpoint.get("epoch", 0)


def main():
    parser = argparse.ArgumentParser(description="Train P&ID Symbol Detector")

    # Data arguments
    parser.add_argument("--data", "-d", type=str, default="data/synthetic",
                        help="Path to training data directory")
    parser.add_argument("--val-split", type=float, default=0.1,
                        help="Validation split ratio")

    # Training arguments
    parser.add_argument("--epochs", "-e", type=int, default=50,
                        help="Number of training epochs")
    parser.add_argument("--batch-size", "-b", type=int, default=4,
                        help="Batch size for training")
    parser.add_argument("--lr", type=float, default=0.005,
                        help="Learning rate")
    parser.add_argument("--momentum", type=float, default=0.9,
                        help="SGD momentum")
    parser.add_argument("--weight-decay", type=float, default=0.0005,
                        help="Weight decay")

    # Model arguments
    parser.add_argument("--backbone", type=str, default="resnet50",
                        choices=["resnet50", "mobilenet_v3_small", "mobilenet_v3_large"],
                        help="Backbone architecture (resnet50 ~160MB, mobilenet_v3_small ~35MB)")
    parser.add_argument("--pretrained", action="store_true", default=True,
                        help="Use pretrained backbone")
    parser.add_argument("--confidence-threshold", type=float, default=0.5,
                        help="Confidence threshold for predictions")
    parser.add_argument("--num-classes", type=int, default=None,
                        help="Number of classes (auto-detected if not specified)")

    # Output arguments
    parser.add_argument("--output", "-o", type=str, default="models",
                        help="Output directory for checkpoints")
    parser.add_argument("--resume", type=str, default=None,
                        help="Path to checkpoint to resume from")
    parser.add_argument("--save-fp16", action="store_true",
                        help="Save final model in FP16 format (smaller size)")

    # Other arguments
    parser.add_argument("--device", type=str, default=None,
                        help="Device to use (cuda/cpu)")
    parser.add_argument("--workers", type=int, default=4,
                        help="Number of data loader workers")
    parser.add_argument("--print-freq", type=int, default=10,
                        help="Print frequency")

    args = parser.parse_args()

    # Set device
    if args.device:
        device = torch.device(args.device)
    else:
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    print(f"Using device: {device}")

    # Create output directory
    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Load dataset
    print(f"Loading dataset from {args.data}...")
    full_dataset = PIDDataset(args.data, transforms=get_train_transforms())
    print(f"Total samples: {len(full_dataset)}")

    # Auto-detect number of classes from dataset
    if args.num_classes is None:
        num_classes = len(full_dataset.categories)
        print(f"Auto-detected {num_classes} classes from dataset")
    else:
        num_classes = args.num_classes
        print(f"Using {num_classes} classes (specified)")

    # Split into train/val
    val_size = int(len(full_dataset) * args.val_split)
    train_size = len(full_dataset) - val_size

    train_dataset, val_dataset = random_split(
        full_dataset,
        [train_size, val_size],
        generator=torch.Generator().manual_seed(42)
    )

    # Override transforms for validation
    val_dataset.dataset = PIDDataset(args.data, transforms=get_val_transforms())

    print(f"Train samples: {len(train_dataset)}")
    print(f"Val samples: {len(val_dataset)}")

    # Create data loaders
    train_loader = DataLoader(
        train_dataset,
        batch_size=args.batch_size,
        shuffle=True,
        num_workers=args.workers,
        collate_fn=collate_fn,
        pin_memory=True if device.type == "cuda" else False,
    )

    val_loader = DataLoader(
        val_dataset,
        batch_size=args.batch_size,
        shuffle=False,
        num_workers=args.workers,
        collate_fn=collate_fn,
        pin_memory=True if device.type == "cuda" else False,
    )

    # Create model
    print(f"Creating model with {num_classes + 1} classes (including background)...")
    print(f"Backbone: {args.backbone}")

    if args.backbone == "resnet50":
        model = SymbolDetector(
            num_classes=num_classes + 1,  # +1 for background
            pretrained=args.pretrained,
            confidence_threshold=args.confidence_threshold,
        )
    else:
        model = MobileSymbolDetector(
            num_classes=num_classes + 1,  # +1 for background
            backbone=args.backbone,
            pretrained=args.pretrained,
            confidence_threshold=args.confidence_threshold,
        )

    model.to(device)

    # Print model size estimate
    total_params = sum(p.numel() for p in model.parameters())
    print(f"Model parameters: {total_params:,} ({total_params * 4 / 1024 / 1024:.1f} MB FP32, {total_params * 2 / 1024 / 1024:.1f} MB FP16)")

    # Create optimizer
    params = [p for p in model.parameters() if p.requires_grad]
    optimizer = torch.optim.SGD(
        params,
        lr=args.lr,
        momentum=args.momentum,
        weight_decay=args.weight_decay,
    )

    # Learning rate scheduler
    lr_scheduler = torch.optim.lr_scheduler.StepLR(
        optimizer,
        step_size=10,
        gamma=0.1,
    )

    # Resume from checkpoint
    start_epoch = 0
    if args.resume:
        print(f"Resuming from {args.resume}...")
        start_epoch = load_checkpoint(args.resume, model, optimizer)
        print(f"Resumed from epoch {start_epoch}")

    # Training history
    history = {
        "train_loss": [],
        "val_loss": [],
        "lr": [],
    }

    best_val_loss = float("inf")
    start_time = time.time()

    print(f"\nStarting training for {args.epochs} epochs...")
    print("=" * 60)

    for epoch in range(start_epoch, args.epochs):
        epoch_start = time.time()

        # Train
        train_metrics = train_one_epoch(
            model, optimizer, train_loader, device, epoch + 1, args.print_freq
        )

        # Validate
        val_metrics = evaluate(model, val_loader, device)

        # Update scheduler
        lr_scheduler.step()
        current_lr = optimizer.param_groups[0]["lr"]

        # Log metrics
        history["train_loss"].append(train_metrics["loss"])
        history["val_loss"].append(val_metrics["val_loss"])
        history["lr"].append(current_lr)

        epoch_time = time.time() - epoch_start

        print(f"Epoch {epoch + 1}/{args.epochs} - "
              f"Train Loss: {train_metrics['loss']:.4f} - "
              f"Val Loss: {val_metrics['val_loss']:.4f} - "
              f"LR: {current_lr:.6f} - "
              f"Time: {epoch_time:.1f}s")

        # Save checkpoint
        checkpoint_path = output_dir / f"checkpoint_epoch_{epoch + 1}.pt"
        save_checkpoint(model, optimizer, epoch + 1, {**train_metrics, **val_metrics}, str(checkpoint_path))

        # Save best model
        if val_metrics["val_loss"] < best_val_loss:
            best_val_loss = val_metrics["val_loss"]
            best_path = output_dir / "best_model.pt"
            model.save(str(best_path))
            print(f"  Saved best model with val_loss: {best_val_loss:.4f}")

    # Save final model
    final_path = output_dir / "final_model.pt"
    model.save(str(final_path))

    # Save FP16 version if requested (for smaller deployment size)
    if args.save_fp16:
        fp16_path = output_dir / "symbol_detector.pt"
        state_dict = model.model.state_dict()
        fp16_state_dict = {k: v.half() if v.dtype == torch.float32 else v
                          for k, v in state_dict.items()}
        checkpoint = {
            "model_state_dict": fp16_state_dict,
            "num_classes": model.num_classes,
            "confidence_threshold": model.confidence_threshold,
            "dtype": "float16",
        }
        if hasattr(model, "backbone_name"):
            checkpoint["backbone_name"] = model.backbone_name
        torch.save(checkpoint, fp16_path)
        fp16_size = fp16_path.stat().st_size / (1024 * 1024)
        print(f"Saved FP16 model to {fp16_path} ({fp16_size:.1f} MB)")

    # Save training history
    history_path = output_dir / "training_history.json"
    with open(history_path, "w") as f:
        json.dump(history, f, indent=2)

    total_time = time.time() - start_time
    print("=" * 60)
    print(f"Training complete in {total_time / 60:.1f} minutes")
    print(f"Best validation loss: {best_val_loss:.4f}")
    print(f"Models saved to: {output_dir}")


if __name__ == "__main__":
    main()

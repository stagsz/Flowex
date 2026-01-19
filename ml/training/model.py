"""
Symbol Detection Model

ResNet-50 + FPN (Feature Pyramid Network) architecture for P&ID symbol detection.
Based on Faster R-CNN with custom modifications for engineering symbols.
"""

import torch
import torch.nn as nn
import torchvision
from torchvision.models.detection import FasterRCNN
from torchvision.models.detection.backbone_utils import BackboneWithFPN
from torchvision.models.detection.rpn import AnchorGenerator
from torchvision.ops import misc as misc_nn_ops

from symbol_classes import NUM_CLASSES


def create_symbol_detector(
    num_classes: int = NUM_CLASSES + 1,  # +1 for background
    pretrained_backbone: bool = True,
    trainable_backbone_layers: int = 3,
    min_size: int = 800,
    max_size: int = 1333,
) -> FasterRCNN:
    """
    Create a Faster R-CNN model with ResNet-50 + FPN backbone.

    Args:
        num_classes: Number of classes (including background)
        pretrained_backbone: Whether to use ImageNet pretrained weights
        trainable_backbone_layers: Number of trainable backbone layers (0-5)
        min_size: Minimum image size for training
        max_size: Maximum image size for training

    Returns:
        FasterRCNN model
    """
    # Load pretrained ResNet-50
    weights = "IMAGENET1K_V1" if pretrained_backbone else None
    backbone = torchvision.models.resnet50(weights=weights)

    # Freeze early layers
    layers_to_freeze = 5 - trainable_backbone_layers
    if layers_to_freeze > 0:
        for name, parameter in backbone.named_parameters():
            if any(f"layer{i}" not in name for i in range(layers_to_freeze, 5)):
                if "layer" in name:
                    layer_num = int(name.split(".")[0].replace("layer", ""))
                    if layer_num < layers_to_freeze:
                        parameter.requires_grad_(False)

    # Create FPN backbone
    return_layers = {"layer1": "0", "layer2": "1", "layer3": "2", "layer4": "3"}
    in_channels_list = [256, 512, 1024, 2048]
    out_channels = 256

    backbone_with_fpn = BackboneWithFPN(
        backbone,
        return_layers=return_layers,
        in_channels_list=in_channels_list,
        out_channels=out_channels,
        extra_blocks=torchvision.ops.feature_pyramid_network.LastLevelMaxPool(),
    )

    # Custom anchor generator for P&ID symbols
    # P&ID symbols tend to be roughly square with various sizes
    anchor_sizes = ((32,), (64,), (128,), (256,), (512,))
    aspect_ratios = ((0.5, 1.0, 2.0),) * len(anchor_sizes)
    anchor_generator = AnchorGenerator(sizes=anchor_sizes, aspect_ratios=aspect_ratios)

    # ROI pooler
    roi_pooler = torchvision.ops.MultiScaleRoIAlign(
        featmap_names=["0", "1", "2", "3"],
        output_size=7,
        sampling_ratio=2,
    )

    # Create Faster R-CNN model
    model = FasterRCNN(
        backbone_with_fpn,
        num_classes=num_classes,
        rpn_anchor_generator=anchor_generator,
        box_roi_pool=roi_pooler,
        min_size=min_size,
        max_size=max_size,
        # RPN settings
        rpn_pre_nms_top_n_train=2000,
        rpn_pre_nms_top_n_test=1000,
        rpn_post_nms_top_n_train=2000,
        rpn_post_nms_top_n_test=1000,
        rpn_nms_thresh=0.7,
        rpn_fg_iou_thresh=0.7,
        rpn_bg_iou_thresh=0.3,
        # Box settings
        box_score_thresh=0.05,
        box_nms_thresh=0.5,
        box_detections_per_img=100,
        box_fg_iou_thresh=0.5,
        box_bg_iou_thresh=0.5,
    )

    return model


class SymbolDetector(nn.Module):
    """
    Wrapper class for the symbol detection model with additional utilities.
    """

    def __init__(
        self,
        num_classes: int = NUM_CLASSES + 1,
        pretrained: bool = True,
        confidence_threshold: float = 0.5,
    ):
        super().__init__()
        self.num_classes = num_classes
        self.confidence_threshold = confidence_threshold
        self.model = create_symbol_detector(
            num_classes=num_classes,
            pretrained_backbone=pretrained,
        )

    def forward(self, images, targets=None):
        """Forward pass - handles both training and inference."""
        return self.model(images, targets)

    def predict(self, image: torch.Tensor) -> dict:
        """
        Run inference on a single image.

        Args:
            image: Tensor of shape (C, H, W)

        Returns:
            Dict with boxes, labels, and scores
        """
        self.eval()
        with torch.no_grad():
            predictions = self.model([image])[0]

        # Filter by confidence threshold
        mask = predictions["scores"] >= self.confidence_threshold
        return {
            "boxes": predictions["boxes"][mask],
            "labels": predictions["labels"][mask],
            "scores": predictions["scores"][mask],
        }

    def save(self, path: str) -> None:
        """Save model weights."""
        torch.save(
            {
                "model_state_dict": self.model.state_dict(),
                "num_classes": self.num_classes,
                "confidence_threshold": self.confidence_threshold,
            },
            path,
        )

    @classmethod
    def load(cls, path: str, device: str = "cpu") -> "SymbolDetector":
        """Load model from checkpoint."""
        checkpoint = torch.load(path, map_location=device)
        model = cls(
            num_classes=checkpoint["num_classes"],
            pretrained=False,
            confidence_threshold=checkpoint.get("confidence_threshold", 0.5),
        )
        model.model.load_state_dict(checkpoint["model_state_dict"])
        return model


def export_to_onnx(
    model: SymbolDetector,
    output_path: str,
    input_size: tuple[int, int] = (800, 800),
) -> None:
    """
    Export model to ONNX format for production deployment.

    Args:
        model: Trained SymbolDetector model
        output_path: Path to save ONNX model
        input_size: Input image size (H, W)
    """
    model.eval()
    dummy_input = torch.randn(1, 3, input_size[0], input_size[1])

    torch.onnx.export(
        model.model,
        dummy_input,
        output_path,
        opset_version=11,
        input_names=["image"],
        output_names=["boxes", "labels", "scores"],
        dynamic_axes={
            "image": {0: "batch_size", 2: "height", 3: "width"},
            "boxes": {0: "num_detections"},
            "labels": {0: "num_detections"},
            "scores": {0: "num_detections"},
        },
    )
    print(f"Model exported to {output_path}")


if __name__ == "__main__":
    # Test model creation
    print("Creating symbol detection model...")
    model = SymbolDetector(num_classes=NUM_CLASSES + 1, pretrained=True)
    print(f"Model created with {NUM_CLASSES + 1} classes (including background)")

    # Test forward pass
    dummy_image = torch.randn(3, 800, 800)
    model.eval()
    with torch.no_grad():
        result = model.predict(dummy_image)
        print(f"Test prediction: {len(result['boxes'])} detections")

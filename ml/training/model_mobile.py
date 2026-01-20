"""
Lightweight Symbol Detection Model

MobileNetV3 + FPN backbone for P&ID symbol detection.
Optimized for small model size (~15-20MB) while maintaining reasonable accuracy.
"""

import torch
import torch.nn as nn
import torchvision
from torchvision.models.detection import FasterRCNN
from torchvision.models.detection.backbone_utils import BackboneWithFPN
from torchvision.models.detection.rpn import AnchorGenerator
from torchvision.models import mobilenet_v3_small, mobilenet_v3_large, MobileNet_V3_Small_Weights, MobileNet_V3_Large_Weights

# Default number of classes (can be overridden)
NUM_CLASSES = 50


def create_mobilenet_backbone(
    backbone_name: str = "mobilenet_v3_small",
    pretrained: bool = True,
    trainable_layers: int = 3,
) -> BackboneWithFPN:
    """
    Create a MobileNetV3 backbone with FPN.

    Args:
        backbone_name: "mobilenet_v3_small" (~2.5M params) or "mobilenet_v3_large" (~5.4M params)
        pretrained: Use ImageNet pretrained weights
        trainable_layers: Number of trainable layers (0-6)

    Returns:
        BackboneWithFPN for Faster R-CNN
    """
    if backbone_name == "mobilenet_v3_small":
        weights = MobileNet_V3_Small_Weights.IMAGENET1K_V1 if pretrained else None
        backbone = mobilenet_v3_small(weights=weights)
        # MobileNetV3-Small architecture:
        # 0: Conv2dNormActivation (16ch)
        # 1: InvertedResidual (16ch)
        # 2-3: InvertedResidual (24ch)
        # 4-6: InvertedResidual (40ch)
        # 7-8: InvertedResidual (48ch)
        # 9-11: InvertedResidual (96ch)
        # 12: Conv2dNormActivation (576ch)
        in_channels_list = [24, 40, 96, 576]
        return_layers = {"3": "0", "6": "1", "11": "2", "12": "3"}
    else:
        weights = MobileNet_V3_Large_Weights.IMAGENET1K_V1 if pretrained else None
        backbone = mobilenet_v3_large(weights=weights)
        # MobileNetV3-Large architecture:
        # 0: Conv (16ch)
        # 1-2: InvertedResidual (16, 24ch)
        # 3-4: InvertedResidual (24, 40ch)
        # 5-7: InvertedResidual (40, 80ch)
        # 8-10: InvertedResidual (80, 112ch)
        # 11-13: InvertedResidual (112, 160ch)
        # 14-15: InvertedResidual (160ch)
        # 16: Conv (960ch)
        in_channels_list = [40, 80, 160, 960]
        return_layers = {"4": "0", "7": "1", "13": "2", "16": "3"}

    # Get the features (all layers except classifier)
    backbone = backbone.features

    # Freeze early layers based on trainable_layers setting
    total_layers = len(backbone)
    layers_to_freeze = total_layers - trainable_layers
    for idx, layer in enumerate(backbone):
        if idx < layers_to_freeze:
            for param in layer.parameters():
                param.requires_grad_(False)

    # Create FPN
    out_channels = 256
    backbone_with_fpn = BackboneWithFPN(
        backbone,
        return_layers=return_layers,
        in_channels_list=in_channels_list,
        out_channels=out_channels,
        extra_blocks=torchvision.ops.feature_pyramid_network.LastLevelMaxPool(),
    )

    return backbone_with_fpn


def create_mobile_symbol_detector(
    num_classes: int = NUM_CLASSES + 1,  # +1 for background
    backbone_name: str = "mobilenet_v3_small",
    pretrained_backbone: bool = True,
    trainable_backbone_layers: int = 3,
    min_size: int = 640,
    max_size: int = 1024,
) -> FasterRCNN:
    """
    Create a lightweight Faster R-CNN model with MobileNetV3 backbone.

    Args:
        num_classes: Number of classes (including background)
        backbone_name: "mobilenet_v3_small" or "mobilenet_v3_large"
        pretrained_backbone: Whether to use ImageNet pretrained weights
        trainable_backbone_layers: Number of trainable backbone layers
        min_size: Minimum image size for training
        max_size: Maximum image size for training

    Returns:
        FasterRCNN model
    """
    # Create backbone with FPN
    backbone_with_fpn = create_mobilenet_backbone(
        backbone_name=backbone_name,
        pretrained=pretrained_backbone,
        trainable_layers=trainable_backbone_layers,
    )

    # Custom anchor generator for P&ID symbols
    anchor_sizes = ((16,), (32,), (64,), (128,), (256,))
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
        # RPN settings (tuned for smaller model)
        rpn_pre_nms_top_n_train=1000,
        rpn_pre_nms_top_n_test=500,
        rpn_post_nms_top_n_train=1000,
        rpn_post_nms_top_n_test=500,
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


class MobileSymbolDetector(nn.Module):
    """
    Wrapper class for the lightweight symbol detection model.
    """

    def __init__(
        self,
        num_classes: int = NUM_CLASSES + 1,
        backbone: str = "mobilenet_v3_small",
        pretrained: bool = True,
        confidence_threshold: float = 0.5,
    ):
        super().__init__()
        self.num_classes = num_classes
        self.backbone_name = backbone
        self.confidence_threshold = confidence_threshold
        self.model = create_mobile_symbol_detector(
            num_classes=num_classes,
            backbone_name=backbone,
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
                "backbone_name": self.backbone_name,
                "confidence_threshold": self.confidence_threshold,
            },
            path,
        )

    @classmethod
    def load(cls, path: str, device: str = "cpu") -> "MobileSymbolDetector":
        """Load model from checkpoint."""
        checkpoint = torch.load(path, map_location=device, weights_only=False)
        model = cls(
            num_classes=checkpoint["num_classes"],
            backbone=checkpoint.get("backbone_name", "mobilenet_v3_small"),
            pretrained=False,
            confidence_threshold=checkpoint.get("confidence_threshold", 0.5),
        )
        model.model.load_state_dict(checkpoint["model_state_dict"])
        return model

    def count_parameters(self) -> dict:
        """Count trainable and total parameters."""
        total = sum(p.numel() for p in self.parameters())
        trainable = sum(p.numel() for p in self.parameters() if p.requires_grad)
        return {
            "total": total,
            "trainable": trainable,
            "total_mb": total * 4 / (1024 * 1024),  # FP32
            "total_mb_fp16": total * 2 / (1024 * 1024),  # FP16
        }


def export_to_onnx(
    model: MobileSymbolDetector,
    output_path: str,
    input_size: tuple[int, int] = (640, 640),
) -> None:
    """
    Export model to ONNX format for production deployment.

    Args:
        model: Trained MobileSymbolDetector model
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
    print("="*60)
    print("MobileNetV3 Symbol Detector - Model Size Comparison")
    print("="*60)

    for backbone in ["mobilenet_v3_small", "mobilenet_v3_large"]:
        print(f"\nBackbone: {backbone}")
        model = MobileSymbolDetector(
            num_classes=NUM_CLASSES + 1,
            backbone=backbone,
            pretrained=True,
        )
        params = model.count_parameters()
        print(f"  Total parameters:     {params['total']:,}")
        print(f"  Trainable parameters: {params['trainable']:,}")
        print(f"  Estimated size (FP32): {params['total_mb']:.1f} MB")
        print(f"  Estimated size (FP16): {params['total_mb_fp16']:.1f} MB")

        # Test forward pass
        model.eval()
        dummy_image = torch.randn(3, 640, 640)
        with torch.no_grad():
            result = model.predict(dummy_image)
            print(f"  Test prediction: {len(result['boxes'])} detections")

    print("\n" + "="*60)
    print("Comparison with ResNet-50 backbone:")
    print("  ResNet-50:        ~160 MB (FP32), ~80 MB (FP16)")
    print("  MobileNetV3-Small: ~15 MB (FP32),  ~8 MB (FP16)")
    print("  MobileNetV3-Large: ~25 MB (FP32), ~13 MB (FP16)")
    print("="*60)

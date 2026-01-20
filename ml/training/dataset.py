"""
P&ID Symbol Detection Dataset

PyTorch Dataset for loading P&ID images with COCO format annotations.
"""

import json
from pathlib import Path

import torch
from PIL import Image
from torch.utils.data import Dataset
from torchvision import transforms as T
from torchvision.transforms import InterpolationMode


class PIDDataset(Dataset):
    """
    Dataset for P&ID symbol detection.

    Expects COCO format annotations with bounding boxes.
    """

    def __init__(
        self,
        root: str,
        annotations_file: str = "annotations.json",
        transforms=None,
        train: bool = True,
    ):
        """
        Args:
            root: Root directory containing images/ folder
            annotations_file: Name of COCO format annotations file
            transforms: Optional transforms to apply
            train: Whether this is training set (enables augmentation)
        """
        self.root = Path(root)
        self.transforms = transforms
        self.train = train

        # Load annotations
        annotations_path = self.root / annotations_file
        with open(annotations_path) as f:
            self.coco = json.load(f)

        # Build lookup dictionaries
        self.images = {img["id"]: img for img in self.coco["images"]}
        self.categories = {cat["id"]: cat for cat in self.coco["categories"]}

        # Group annotations by image
        self.img_annotations: dict[int, list] = {}
        for ann in self.coco["annotations"]:
            img_id = ann["image_id"]
            if img_id not in self.img_annotations:
                self.img_annotations[img_id] = []
            self.img_annotations[img_id].append(ann)

        # Get list of image IDs that have annotations
        self.image_ids = list(self.img_annotations.keys())

    def __len__(self) -> int:
        return len(self.image_ids)

    def __getitem__(self, idx: int) -> tuple[torch.Tensor, dict]:
        # Get image info
        img_id = self.image_ids[idx]
        img_info = self.images[img_id]

        # Load image
        img_path = self.root / "images" / img_info["file_name"]
        image = Image.open(img_path).convert("RGB")

        # Get annotations for this image
        annotations = self.img_annotations.get(img_id, [])

        # Convert to tensors
        boxes = []
        labels = []
        areas = []
        iscrowd = []

        for ann in annotations:
            # COCO format: [x, y, width, height]
            x, y, w, h = ann["bbox"]
            # Convert to [x1, y1, x2, y2]
            boxes.append([x, y, x + w, y + h])
            labels.append(ann["category_id"])
            areas.append(ann["area"])
            iscrowd.append(ann.get("iscrowd", 0))

        # Convert to tensors
        if boxes:
            boxes = torch.as_tensor(boxes, dtype=torch.float32)
            labels = torch.as_tensor(labels, dtype=torch.int64)
            areas = torch.as_tensor(areas, dtype=torch.float32)
            iscrowd = torch.as_tensor(iscrowd, dtype=torch.int64)
        else:
            # Empty annotations
            boxes = torch.zeros((0, 4), dtype=torch.float32)
            labels = torch.zeros((0,), dtype=torch.int64)
            areas = torch.zeros((0,), dtype=torch.float32)
            iscrowd = torch.zeros((0,), dtype=torch.int64)

        target = {
            "boxes": boxes,
            "labels": labels,
            "image_id": torch.tensor([img_id]),
            "area": areas,
            "iscrowd": iscrowd,
        }

        # Apply transforms
        if self.transforms:
            image, target = self.transforms(image, target)
        else:
            # Default: convert to tensor
            image = T.ToTensor()(image)

        return image, target


class Compose:
    """Compose transforms for detection."""

    def __init__(self, transforms):
        self.transforms = transforms

    def __call__(self, image, target):
        for t in self.transforms:
            image, target = t(image, target)
        return image, target


class Resize:
    """Resize image and bounding boxes to max size."""

    def __init__(self, max_size: int = 1024):
        self.max_size = max_size

    def __call__(self, image, target):
        # Get original size
        if hasattr(image, 'size'):
            orig_w, orig_h = image.size
        else:
            orig_h, orig_w = image.shape[-2:]

        # Calculate scale
        scale = min(self.max_size / orig_w, self.max_size / orig_h)

        if scale < 1.0:
            # Resize image
            new_w = int(orig_w * scale)
            new_h = int(orig_h * scale)

            if hasattr(image, 'resize'):
                image = image.resize((new_w, new_h), Image.BILINEAR)
            else:
                image = T.functional.resize(image, (new_h, new_w))

            # Scale bounding boxes
            if "boxes" in target and len(target["boxes"]) > 0:
                boxes = target["boxes"].clone().float()
                boxes *= scale
                target["boxes"] = boxes

        return image, target


class ToTensor:
    """Convert PIL Image to Tensor."""

    def __call__(self, image, target):
        image = T.ToTensor()(image)
        return image, target


class RandomHorizontalFlip:
    """Random horizontal flip for detection."""

    def __init__(self, prob: float = 0.5):
        self.prob = prob

    def __call__(self, image, target):
        import random
        if random.random() < self.prob:
            image = T.functional.hflip(image)

            # Flip bounding boxes
            if "boxes" in target and len(target["boxes"]) > 0:
                # Get width from PIL image or tensor
                if hasattr(image, 'size'):
                    width = image.size[0]  # PIL Image
                else:
                    width = image.shape[-1]  # Tensor
                boxes = target["boxes"].clone()
                boxes[:, [0, 2]] = width - boxes[:, [2, 0]]
                target["boxes"] = boxes

        return image, target


class ColorJitter:
    """Random color jittering."""

    def __init__(
        self,
        brightness: float = 0.2,
        contrast: float = 0.2,
        saturation: float = 0.2,
        hue: float = 0.1,
    ):
        self.jitter = T.ColorJitter(brightness, contrast, saturation, hue)

    def __call__(self, image, target):
        # ColorJitter works on PIL images
        if not isinstance(image, torch.Tensor):
            image = self.jitter(image)
        else:
            # Convert tensor to PIL, apply jitter, convert back
            image = T.ToPILImage()(image)
            image = self.jitter(image)
            image = T.ToTensor()(image)
        return image, target


def get_train_transforms(max_size: int = 1024):
    """Get transforms for training."""
    return Compose([
        Resize(max_size),
        RandomHorizontalFlip(0.5),
        ColorJitter(0.2, 0.2, 0.2, 0.1),
        ToTensor(),
    ])


def get_val_transforms(max_size: int = 1024):
    """Get transforms for validation."""
    return Compose([
        Resize(max_size),
        ToTensor(),
    ])


def collate_fn(batch):
    """Custom collate function for detection."""
    return tuple(zip(*batch))


if __name__ == "__main__":
    # Test dataset loading
    import sys

    if len(sys.argv) > 1:
        data_path = sys.argv[1]
    else:
        data_path = "data/synthetic"

    print(f"Testing dataset from {data_path}")

    dataset = PIDDataset(data_path, transforms=get_train_transforms())
    print(f"Dataset size: {len(dataset)}")

    if len(dataset) > 0:
        image, target = dataset[0]
        print(f"Image shape: {image.shape}")
        print(f"Boxes: {target['boxes'].shape}")
        print(f"Labels: {target['labels']}")

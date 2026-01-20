"""
Convert DigitizePID_Dataset to COCO format for training.

The DigitizePID dataset has:
- image_2/*.jpg - P&ID images
- {id}/{id}_symbols.npy - Symbol annotations [name, [x1,y1,x2,y2], class_id]
- {id}/{id}_words.npy - Text annotations
- {id}/{id}_lines.npy - Line annotations
"""

import json
import os
import shutil
from datetime import datetime
from pathlib import Path

import numpy as np
from PIL import Image


def load_npy_safe(path: str) -> np.ndarray:
    """Load .npy file with pickle allowed."""
    return np.load(path, allow_pickle=True)


def convert_dataset(
    input_dir: str,
    output_dir: str,
    max_samples: int | None = None,
) -> None:
    """
    Convert DigitizePID dataset to COCO format.

    Args:
        input_dir: Path to DigitizePID_Dataset
        output_dir: Output directory for COCO format dataset
        max_samples: Maximum number of samples to convert (None for all)
    """
    input_path = Path(input_dir)
    output_path = Path(output_dir)
    images_out = output_path / "images"
    images_out.mkdir(parents=True, exist_ok=True)

    # Find all sample directories (numbered folders)
    sample_dirs = sorted([
        d for d in input_path.iterdir()
        if d.is_dir() and d.name.isdigit()
    ], key=lambda x: int(x.name))

    if max_samples:
        sample_dirs = sample_dirs[:max_samples]

    print(f"Found {len(sample_dirs)} samples to convert")

    # Collect all unique class IDs to create category mapping
    all_classes = set()
    for sample_dir in sample_dirs:
        symbols_file = sample_dir / f"{sample_dir.name}_symbols.npy"
        if symbols_file.exists():
            symbols = load_npy_safe(str(symbols_file))
            for row in symbols:
                if len(row) >= 3:
                    all_classes.add(str(row[2]))

    # Create category mapping (class_id -> category_id)
    class_to_cat = {cls: idx + 1 for idx, cls in enumerate(sorted(all_classes))}
    print(f"Found {len(class_to_cat)} unique symbol classes")

    # COCO format structure
    coco = {
        "info": {
            "description": "DigitizePID Dataset (converted)",
            "version": "1.0",
            "year": 2026,
            "contributor": "Flowex",
            "date_created": datetime.now().isoformat(),
        },
        "licenses": [],
        "categories": [
            {"id": cat_id, "name": f"symbol_class_{cls}", "supercategory": "symbol"}
            for cls, cat_id in class_to_cat.items()
        ],
        "images": [],
        "annotations": [],
    }

    annotation_id = 1
    images_copied = 0
    total_annotations = 0

    for sample_dir in sample_dirs:
        sample_id = sample_dir.name

        # Find image
        image_path = input_path / "image_2" / f"{sample_id}.jpg"
        if not image_path.exists():
            print(f"  Warning: Image not found for sample {sample_id}")
            continue

        # Load symbols
        symbols_file = sample_dir / f"{sample_id}_symbols.npy"
        if not symbols_file.exists():
            continue

        symbols = load_npy_safe(str(symbols_file))
        if len(symbols) == 0:
            continue

        # Get image dimensions
        with Image.open(image_path) as img:
            width, height = img.size

        # Copy image to output
        out_image_name = f"{sample_id}.jpg"
        shutil.copy(image_path, images_out / out_image_name)

        # Add image info
        image_id = int(sample_id)
        coco["images"].append({
            "id": image_id,
            "file_name": out_image_name,
            "width": width,
            "height": height,
        })
        images_copied += 1

        # Add annotations
        for row in symbols:
            if len(row) < 3:
                continue

            name, bbox_list, class_id = row[0], row[1], str(row[2])

            # Convert bbox from [x1, y1, x2, y2] to [x, y, width, height]
            try:
                bbox = list(bbox_list) if hasattr(bbox_list, '__iter__') else bbox_list
                x1, y1, x2, y2 = float(bbox[0]), float(bbox[1]), float(bbox[2]), float(bbox[3])
                w = x2 - x1
                h = y2 - y1

                if w <= 0 or h <= 0:
                    continue

                cat_id = class_to_cat.get(class_id)
                if cat_id is None:
                    continue

                coco["annotations"].append({
                    "id": annotation_id,
                    "image_id": image_id,
                    "category_id": cat_id,
                    "bbox": [x1, y1, w, h],
                    "area": w * h,
                    "iscrowd": 0,
                })
                annotation_id += 1
                total_annotations += 1

            except (TypeError, ValueError, IndexError) as e:
                continue

        if images_copied % 50 == 0:
            print(f"  Processed {images_copied} images...")

    # Save annotations
    annotations_file = output_path / "annotations.json"
    with open(annotations_file, "w") as f:
        json.dump(coco, f, indent=2)

    # Save class mapping for reference
    mapping_file = output_path / "class_mapping.json"
    with open(mapping_file, "w") as f:
        json.dump(class_to_cat, f, indent=2)

    print(f"\nConversion complete:")
    print(f"  Images: {images_copied}")
    print(f"  Annotations: {total_annotations}")
    print(f"  Categories: {len(class_to_cat)}")
    print(f"  Output: {output_path}")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Convert DigitizePID to COCO format")
    parser.add_argument("--input", "-i", default="../DigitizePID_Dataset",
                        help="Input directory")
    parser.add_argument("--output", "-o", default="../data/digitize_pid",
                        help="Output directory")
    parser.add_argument("--max-samples", "-n", type=int, default=None,
                        help="Max samples to convert")

    args = parser.parse_args()
    convert_dataset(args.input, args.output, args.max_samples)

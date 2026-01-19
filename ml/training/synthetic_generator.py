"""
Synthetic P&ID Generator

Generates synthetic P&ID training images with random symbol placements.
Each image includes bounding box annotations in COCO format.
"""

import json
import math
import os
import random
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from symbol_classes import (
    EQUIPMENT_SYMBOLS,
    INSTRUMENT_SYMBOLS,
    PIPING_SYMBOLS,
    SYMBOL_CLASSES,
    VALVE_SYMBOLS,
    SymbolCategory,
)


@dataclass
class BoundingBox:
    x: float
    y: float
    width: float
    height: float
    class_id: int
    class_name: str


@dataclass
class GeneratedImage:
    image: Image.Image
    boxes: list[BoundingBox]
    filename: str


class SyntheticPIDGenerator:
    """Generator for synthetic P&ID training images."""

    def __init__(
        self,
        image_width: int = 2000,
        image_height: int = 1500,
        min_symbols: int = 10,
        max_symbols: int = 30,
        seed: int | None = None,
    ):
        self.image_width = image_width
        self.image_height = image_height
        self.min_symbols = min_symbols
        self.max_symbols = max_symbols

        if seed is not None:
            random.seed(seed)

        # Symbol size ranges (width, height) in pixels
        self.symbol_sizes = {
            SymbolCategory.EQUIPMENT: (80, 120),
            SymbolCategory.INSTRUMENT: (40, 60),
            SymbolCategory.VALVE: (30, 40),
            SymbolCategory.PIPING: (20, 30),
        }

        # Try to load a font for text
        self.font = None
        try:
            self.font = ImageFont.truetype("arial.ttf", 12)
        except Exception:
            try:
                self.font = ImageFont.load_default()
            except Exception:
                pass

    def generate_image(self) -> GeneratedImage:
        """Generate a single synthetic P&ID image with annotations."""
        # Create white background
        image = Image.new("RGB", (self.image_width, self.image_height), "white")
        draw = ImageDraw.Draw(image)

        boxes: list[BoundingBox] = []
        num_symbols = random.randint(self.min_symbols, self.max_symbols)

        # Draw grid lines (like engineering paper)
        self._draw_grid(draw)

        # Draw title block
        self._draw_title_block(draw)

        # Place symbols
        placed_boxes: list[tuple[int, int, int, int]] = []

        for _ in range(num_symbols):
            # Select random symbol class
            symbol = random.choice(SYMBOL_CLASSES)
            size_range = self.symbol_sizes.get(symbol.category, (40, 60))
            width = random.randint(size_range[0] - 10, size_range[0] + 10)
            height = random.randint(size_range[1] - 10, size_range[1] + 10)

            # Find non-overlapping position
            max_attempts = 50
            for _ in range(max_attempts):
                x = random.randint(50, self.image_width - width - 50)
                y = random.randint(100, self.image_height - height - 150)

                # Check overlap
                new_box = (x, y, x + width, y + height)
                if not self._overlaps(new_box, placed_boxes):
                    placed_boxes.append(new_box)
                    break
            else:
                continue  # Couldn't place symbol, skip

            # Draw symbol
            self._draw_symbol(draw, symbol, x, y, width, height)

            # Add bounding box annotation
            boxes.append(
                BoundingBox(
                    x=x,
                    y=y,
                    width=width,
                    height=height,
                    class_id=symbol.id,
                    class_name=symbol.name,
                )
            )

        # Draw connecting lines between some symbols
        self._draw_connections(draw, placed_boxes)

        # Generate filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        random_id = random.randint(1000, 9999)
        filename = f"synthetic_pid_{timestamp}_{random_id}.png"

        return GeneratedImage(image=image, boxes=boxes, filename=filename)

    def _draw_grid(self, draw: ImageDraw.ImageDraw) -> None:
        """Draw light grid lines."""
        grid_color = (230, 230, 230)
        spacing = 50

        for x in range(0, self.image_width, spacing):
            draw.line([(x, 0), (x, self.image_height)], fill=grid_color, width=1)
        for y in range(0, self.image_height, spacing):
            draw.line([(0, y), (self.image_width, y)], fill=grid_color, width=1)

    def _draw_title_block(self, draw: ImageDraw.ImageDraw) -> None:
        """Draw a title block in the corner."""
        block_width = 300
        block_height = 100
        x = self.image_width - block_width - 20
        y = self.image_height - block_height - 20

        draw.rectangle([x, y, x + block_width, y + block_height], outline="black", width=2)
        draw.line([(x, y + 30), (x + block_width, y + 30)], fill="black", width=1)
        draw.line([(x, y + 60), (x + block_width, y + 60)], fill="black", width=1)

        if self.font:
            draw.text((x + 10, y + 5), "SYNTHETIC P&ID", fill="black", font=self.font)
            draw.text((x + 10, y + 35), f"Drawing: PID-{random.randint(100, 999)}", fill="black", font=self.font)
            draw.text((x + 10, y + 65), "Rev: A", fill="black", font=self.font)

    def _draw_symbol(
        self,
        draw: ImageDraw.ImageDraw,
        symbol,
        x: int,
        y: int,
        width: int,
        height: int,
    ) -> None:
        """Draw a symbol representation."""
        # Different drawing styles based on category
        if symbol.category == SymbolCategory.EQUIPMENT:
            self._draw_equipment(draw, symbol.name, x, y, width, height)
        elif symbol.category == SymbolCategory.INSTRUMENT:
            self._draw_instrument(draw, symbol.name, x, y, width, height)
        elif symbol.category == SymbolCategory.VALVE:
            self._draw_valve(draw, symbol.name, x, y, width, height)
        else:
            self._draw_generic(draw, symbol.name, x, y, width, height)

        # Add tag number
        tag = self._generate_tag(symbol)
        if self.font:
            draw.text((x, y - 15), tag, fill="black", font=self.font)

    def _draw_equipment(self, draw, name: str, x: int, y: int, w: int, h: int) -> None:
        """Draw equipment symbols."""
        if "vessel_vertical" in name or "column" in name or "reactor" in name:
            # Vertical cylinder
            draw.ellipse([x, y, x + w, y + h // 6], outline="black", width=2)
            draw.ellipse([x, y + h - h // 6, x + w, y + h], outline="black", width=2)
            draw.line([(x, y + h // 12), (x, y + h - h // 12)], fill="black", width=2)
            draw.line([(x + w, y + h // 12), (x + w, y + h - h // 12)], fill="black", width=2)
        elif "vessel_horizontal" in name or "tank" in name:
            # Horizontal cylinder
            draw.ellipse([x, y, x + w // 6, y + h], outline="black", width=2)
            draw.ellipse([x + w - w // 6, y, x + w, y + h], outline="black", width=2)
            draw.line([(x + w // 12, y), (x + w - w // 12, y)], fill="black", width=2)
            draw.line([(x + w // 12, y + h), (x + w - w // 12, y + h)], fill="black", width=2)
        elif "pump" in name:
            # Circle with triangle
            draw.ellipse([x, y, x + w, y + h], outline="black", width=2)
            cx, cy = x + w // 2, y + h // 2
            r = min(w, h) // 3
            points = [
                (cx - r, cy - r // 2),
                (cx - r, cy + r // 2),
                (cx + r, cy),
            ]
            draw.polygon(points, outline="black", width=2)
        elif "heat_exchanger" in name:
            # Rectangle with internal lines
            draw.rectangle([x, y, x + w, y + h], outline="black", width=2)
            for i in range(1, 4):
                lx = x + (w * i) // 4
                draw.line([(lx, y), (lx, y + h)], fill="black", width=1)
        elif "compressor" in name or "blower" in name:
            # Circle with curved arrow
            draw.ellipse([x, y, x + w, y + h], outline="black", width=2)
            # Arrow inside
            cx, cy = x + w // 2, y + h // 2
            draw.arc([x + 5, y + 5, x + w - 5, y + h - 5], 0, 270, fill="black", width=2)
        else:
            # Generic rectangle
            draw.rectangle([x, y, x + w, y + h], outline="black", width=2)

    def _draw_instrument(self, draw, name: str, x: int, y: int, w: int, h: int) -> None:
        """Draw instrument symbols."""
        cx, cy = x + w // 2, y + h // 2
        r = min(w, h) // 2

        if "transmitter" in name or "indicator" in name or "controller" in name:
            # Circle (local) or circle with line (panel)
            draw.ellipse([cx - r, cy - r, cx + r, cy + r], outline="black", width=2)
            if "panel" in name or "dcs" in name:
                draw.line([(cx - r, cy), (cx + r, cy)], fill="black", width=1)
        elif "switch" in name or "alarm" in name:
            # Diamond shape
            points = [
                (cx, cy - r),
                (cx + r, cy),
                (cx, cy + r),
                (cx - r, cy),
            ]
            draw.polygon(points, outline="black", width=2)
        elif "orifice" in name:
            # Two parallel lines
            draw.line([(x, y + h // 2 - 5), (x + w, y + h // 2 - 5)], fill="black", width=2)
            draw.line([(x, y + h // 2 + 5), (x + w, y + h // 2 + 5)], fill="black", width=2)
        else:
            # Default circle
            draw.ellipse([cx - r, cy - r, cx + r, cy + r], outline="black", width=2)

    def _draw_valve(self, draw, name: str, x: int, y: int, w: int, h: int) -> None:
        """Draw valve symbols."""
        cx, cy = x + w // 2, y + h // 2

        if "check" in name:
            # Triangle with line
            points = [(x, y), (x + w, cy), (x, y + h)]
            draw.polygon(points, outline="black", width=2)
            draw.line([(x + w, y), (x + w, y + h)], fill="black", width=2)
        elif "relief" in name or "safety" in name:
            # Triangle pointing up
            points = [(cx, y), (x + w, y + h), (x, y + h)]
            draw.polygon(points, outline="black", width=2)
        elif "control" in name:
            # Two triangles with actuator
            draw.polygon([(x, y), (cx, cy), (x, y + h)], outline="black", width=2)
            draw.polygon([(x + w, y), (cx, cy), (x + w, y + h)], outline="black", width=2)
            # Actuator
            draw.rectangle([cx - 5, y - 15, cx + 5, y], outline="black", width=1)
        elif "butterfly" in name:
            # Circle with line through
            draw.ellipse([x, y, x + w, y + h], outline="black", width=2)
            draw.line([(x, cy), (x + w, cy)], fill="black", width=2)
        else:
            # Standard gate/globe valve (two triangles)
            draw.polygon([(x, y), (cx, cy), (x, y + h)], outline="black", width=2)
            draw.polygon([(x + w, y), (cx, cy), (x + w, y + h)], outline="black", width=2)

    def _draw_generic(self, draw, name: str, x: int, y: int, w: int, h: int) -> None:
        """Draw generic symbol."""
        draw.rectangle([x, y, x + w, y + h], outline="black", width=2)

    def _draw_connections(self, draw: ImageDraw.ImageDraw, boxes: list[tuple]) -> None:
        """Draw random connecting lines between symbols."""
        if len(boxes) < 2:
            return

        num_connections = min(len(boxes) // 2, 10)
        for _ in range(num_connections):
            box1, box2 = random.sample(boxes, 2)
            x1 = (box1[0] + box1[2]) // 2
            y1 = (box1[1] + box1[3]) // 2
            x2 = (box2[0] + box2[2]) // 2
            y2 = (box2[1] + box2[3]) // 2

            # Draw line with potential bends
            if random.random() > 0.5:
                # L-shaped connection
                mid_x = x1
                draw.line([(x1, y1), (mid_x, y2), (x2, y2)], fill="black", width=2)
            else:
                # Direct line
                draw.line([(x1, y1), (x2, y2)], fill="black", width=2)

    def _generate_tag(self, symbol) -> str:
        """Generate a realistic tag number for a symbol."""
        if symbol.category == SymbolCategory.EQUIPMENT:
            prefixes = ["V", "T", "P", "E", "C", "R", "F"]
            prefix = random.choice(prefixes)
            return f"{prefix}-{random.randint(100, 999)}"
        elif symbol.category == SymbolCategory.INSTRUMENT:
            # ISA-style tags
            measured = random.choice(["P", "T", "F", "L", "A"])
            function = random.choice(["T", "I", "C", "A", "S"])
            return f"{measured}{function}-{random.randint(100, 999)}"
        elif symbol.category == SymbolCategory.VALVE:
            return f"XV-{random.randint(100, 999)}"
        else:
            return f"X-{random.randint(100, 999)}"

    def _overlaps(self, new_box: tuple, existing: list[tuple], margin: int = 20) -> bool:
        """Check if a box overlaps with existing boxes."""
        x1, y1, x2, y2 = new_box
        for ex1, ey1, ex2, ey2 in existing:
            if not (
                x2 + margin < ex1
                or x1 - margin > ex2
                or y2 + margin < ey1
                or y1 - margin > ey2
            ):
                return True
        return False


def generate_dataset(
    output_dir: str,
    num_images: int = 1000,
    seed: int = 42,
) -> None:
    """
    Generate a synthetic P&ID dataset with COCO annotations.

    Args:
        output_dir: Directory to save images and annotations
        num_images: Number of images to generate
        seed: Random seed for reproducibility
    """
    output_path = Path(output_dir)
    images_path = output_path / "images"
    images_path.mkdir(parents=True, exist_ok=True)

    generator = SyntheticPIDGenerator(seed=seed)

    # COCO format annotation structure
    coco_annotations = {
        "info": {
            "description": "Synthetic P&ID Dataset",
            "version": "1.0",
            "year": 2026,
            "contributor": "Flowex",
            "date_created": datetime.now().isoformat(),
        },
        "licenses": [],
        "categories": [
            {"id": s.id, "name": s.name, "supercategory": s.category.value}
            for s in SYMBOL_CLASSES
        ],
        "images": [],
        "annotations": [],
    }

    annotation_id = 1

    print(f"Generating {num_images} synthetic P&ID images...")
    for i in range(num_images):
        result = generator.generate_image()

        # Save image
        image_path = images_path / result.filename
        result.image.save(image_path, "PNG")

        # Add image info
        image_id = i + 1
        coco_annotations["images"].append(
            {
                "id": image_id,
                "file_name": result.filename,
                "width": generator.image_width,
                "height": generator.image_height,
            }
        )

        # Add bounding box annotations
        for box in result.boxes:
            coco_annotations["annotations"].append(
                {
                    "id": annotation_id,
                    "image_id": image_id,
                    "category_id": box.class_id,
                    "bbox": [box.x, box.y, box.width, box.height],
                    "area": box.width * box.height,
                    "iscrowd": 0,
                }
            )
            annotation_id += 1

        if (i + 1) % 100 == 0:
            print(f"  Generated {i + 1}/{num_images} images")

    # Save annotations
    annotations_file = output_path / "annotations.json"
    with open(annotations_file, "w") as f:
        json.dump(coco_annotations, f, indent=2)

    print(f"Dataset generated: {num_images} images, {annotation_id - 1} annotations")
    print(f"Output: {output_path}")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Generate synthetic P&ID training data")
    parser.add_argument("--output", "-o", default="data/synthetic", help="Output directory")
    parser.add_argument("--num-images", "-n", type=int, default=1000, help="Number of images")
    parser.add_argument("--seed", "-s", type=int, default=42, help="Random seed")

    args = parser.parse_args()
    generate_dataset(args.output, args.num_images, args.seed)

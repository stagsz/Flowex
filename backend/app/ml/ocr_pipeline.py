"""
OCR Pipeline for P&ID Text Extraction

Uses Tesseract OCR to extract text from P&ID drawings.
Handles rotated text and engineering-specific tag formats.
"""

import logging
import re
from dataclasses import dataclass
from enum import Enum

import pytesseract
from PIL import Image

logger = logging.getLogger(__name__)


class TagType(str, Enum):
    EQUIPMENT = "equipment"
    INSTRUMENT = "instrument"
    LINE = "line"
    VALVE = "valve"
    UNKNOWN = "unknown"


@dataclass
class ExtractedText:
    text: str
    confidence: float
    bbox: tuple[int, int, int, int]  # x, y, width, height
    rotation: int  # 0, 90, 180, 270
    tag_type: TagType
    normalized_tag: str | None


class OCRPipeline:
    """Pipeline for extracting and classifying text from P&ID images."""

    # Tag patterns for classification
    TAG_PATTERNS = {
        # Equipment tags: V-101, P-201, E-301, etc.
        TagType.EQUIPMENT: re.compile(
            r"^[VPETCRHFBDMS]-\d{3,4}[A-Z]?$", re.IGNORECASE
        ),
        # Instrument tags: PT-101, FT-201, LIC-301, etc. (ISA format)
        TagType.INSTRUMENT: re.compile(
            r"^[PFTLAISWQCYZ][IRTCSDAEHQY]{0,3}-\d{3,4}[A-Z]?$", re.IGNORECASE
        ),
        # Line tags: 6"-P-101-A1, 2"-W-201-B2, etc.
        TagType.LINE: re.compile(
            r'^\d{1,2}["\']-[A-Z]{1,2}-\d{3,4}-[A-Z]\d?$', re.IGNORECASE
        ),
        # Valve tags: XV-101, HV-201, etc.
        TagType.VALVE: re.compile(
            r"^[XHP]V-\d{3,4}[A-Z]?$", re.IGNORECASE
        ),
    }

    def __init__(
        self,
        tesseract_config: str = "--psm 6 --oem 3",
        min_confidence: float = 60.0,
        languages: str = "eng",
    ):
        """
        Initialize OCR pipeline.

        Args:
            tesseract_config: Tesseract configuration string
            min_confidence: Minimum confidence threshold (0-100)
            languages: Tesseract language(s) to use
        """
        self.tesseract_config = tesseract_config
        self.min_confidence = min_confidence
        self.languages = languages

    def extract_text(self, image: Image.Image) -> list[ExtractedText]:
        """
        Extract text from an image.

        Args:
            image: PIL Image to process

        Returns:
            List of ExtractedText objects
        """
        results = []

        # Try different rotations for rotated text
        for rotation in [0, 90, 180, 270]:
            rotated_image = image.rotate(-rotation, expand=True) if rotation else image
            texts = self._extract_at_rotation(rotated_image, rotation)
            results.extend(texts)

        # Deduplicate overlapping detections
        results = self._deduplicate(results)

        return results

    def _extract_at_rotation(
        self, image: Image.Image, rotation: int
    ) -> list[ExtractedText]:
        """Extract text at a specific rotation."""
        results = []

        try:
            # Get detailed OCR data
            data = pytesseract.image_to_data(
                image,
                lang=self.languages,
                config=self.tesseract_config,
                output_type=pytesseract.Output.DICT,
            )

            n_boxes = len(data["text"])
            for i in range(n_boxes):
                text = data["text"][i].strip()
                conf = float(data["conf"][i])

                # Skip empty or low confidence
                if not text or conf < self.min_confidence:
                    continue

                # Get bounding box
                x, y, w, h = (
                    data["left"][i],
                    data["top"][i],
                    data["width"][i],
                    data["height"][i],
                )

                # Classify tag
                tag_type = self._classify_tag(text)
                normalized = self._normalize_tag(text) if tag_type != TagType.UNKNOWN else None

                results.append(
                    ExtractedText(
                        text=text,
                        confidence=conf / 100.0,  # Normalize to 0-1
                        bbox=(x, y, w, h),
                        rotation=rotation,
                        tag_type=tag_type,
                        normalized_tag=normalized,
                    )
                )

        except Exception as e:
            logger.error(f"OCR extraction failed: {e}")

        return results

    def _classify_tag(self, text: str) -> TagType:
        """Classify a text string as a specific tag type."""
        text = text.strip().upper()

        for tag_type, pattern in self.TAG_PATTERNS.items():
            if pattern.match(text):
                return tag_type

        return TagType.UNKNOWN

    def _normalize_tag(self, text: str) -> str:
        """Normalize tag format (uppercase, standard separators)."""
        # Convert to uppercase and strip whitespace
        normalized = text.upper().strip()

        # Note: Common OCR error corrections (0->O, I->1, l->1) could be applied
        # context-sensitively here based on tag format patterns, but for now
        # we rely on the regex validation to catch invalid characters

        return normalized

    def _deduplicate(self, texts: list[ExtractedText]) -> list[ExtractedText]:
        """Remove duplicate detections from different rotations."""
        if not texts:
            return []

        # Sort by confidence (highest first)
        texts.sort(key=lambda t: t.confidence, reverse=True)

        unique = []
        for text in texts:
            # Check if we already have this text (similar bbox)
            is_duplicate = False
            for existing in unique:
                if self._is_same_text(text, existing):
                    is_duplicate = True
                    break

            if not is_duplicate:
                unique.append(text)

        return unique

    def _is_same_text(self, t1: ExtractedText, t2: ExtractedText) -> bool:
        """Check if two text extractions are the same detection."""
        # Same or similar text
        if t1.text.upper() != t2.text.upper():
            return False

        # Overlapping bounding boxes (considering rotation)
        # Simplified check - production would handle coordinate transforms
        return abs(t1.bbox[0] - t2.bbox[0]) < 20 and abs(t1.bbox[1] - t2.bbox[1]) < 20

    def extract_tags_only(self, image: Image.Image) -> list[ExtractedText]:
        """Extract only recognized P&ID tags (equipment, instruments, etc.)."""
        all_text = self.extract_text(image)
        return [t for t in all_text if t.tag_type != TagType.UNKNOWN]


class TagAssociator:
    """Associates extracted tags with detected symbols."""

    def __init__(self, max_distance: float = 100.0):
        """
        Initialize tag associator.

        Args:
            max_distance: Maximum pixel distance for tag-symbol association
        """
        self.max_distance = max_distance

    def associate(
        self,
        texts: list[ExtractedText],
        symbols: list[dict],  # List of {bbox, class_id, class_name}
    ) -> list[dict]:
        """
        Associate tags with nearby symbols.

        Args:
            texts: List of extracted text objects
            symbols: List of detected symbols with bounding boxes

        Returns:
            List of associations {text, symbol, distance}
        """
        associations = []

        for text in texts:
            if text.tag_type == TagType.UNKNOWN:
                continue

            text_center = (
                text.bbox[0] + text.bbox[2] / 2,
                text.bbox[1] + text.bbox[3] / 2,
            )

            best_symbol = None
            best_distance = float("inf")

            for symbol in symbols:
                symbol_bbox = symbol["bbox"]
                symbol_center = (
                    symbol_bbox[0] + symbol_bbox[2] / 2,
                    symbol_bbox[1] + symbol_bbox[3] / 2,
                )

                # Calculate distance
                distance = (
                    (text_center[0] - symbol_center[0]) ** 2
                    + (text_center[1] - symbol_center[1]) ** 2
                ) ** 0.5

                if distance < best_distance and distance < self.max_distance:
                    best_distance = distance
                    best_symbol = symbol

            if best_symbol is not None:
                associations.append(
                    {
                        "text": text,
                        "symbol": best_symbol,
                        "distance": best_distance,
                    }
                )

        return associations


# Singleton instances
_ocr_pipeline: OCRPipeline | None = None


def get_ocr_pipeline() -> OCRPipeline:
    """Get or create the OCR pipeline instance."""
    global _ocr_pipeline
    if _ocr_pipeline is None:
        _ocr_pipeline = OCRPipeline()
    return _ocr_pipeline

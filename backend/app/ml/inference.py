"""
ML Inference Service

Combines symbol detection and OCR for complete P&ID analysis.
"""

import io
import logging
from dataclasses import dataclass
from pathlib import Path

import torch
from PIL import Image

from app.ml.ocr_pipeline import ExtractedText, TagAssociator, get_ocr_pipeline

logger = logging.getLogger(__name__)


@dataclass
class DetectedSymbol:
    class_id: int
    class_name: str
    confidence: float
    bbox: tuple[float, float, float, float]  # x, y, width, height
    tag: str | None = None


@dataclass
class AnalysisResult:
    symbols: list[DetectedSymbol]
    texts: list[ExtractedText]
    associations: list[dict[str, object]]
    image_width: int
    image_height: int


class InferenceService:
    """
    Service for running ML inference on P&ID images.

    Combines:
    - Symbol detection (Faster R-CNN)
    - OCR (Tesseract)
    - Tag-symbol association
    """

    def __init__(
        self,
        model_path: str | None = None,
        device: str | None = None,
        confidence_threshold: float = 0.5,
    ):
        """
        Initialize inference service.

        Args:
            model_path: Path to trained model weights
            device: Device to run inference on (cpu/cuda)
            confidence_threshold: Minimum confidence for detections
        """
        self.device = device or ("cuda" if torch.cuda.is_available() else "cpu")
        self.confidence_threshold = confidence_threshold
        self.model_path = model_path

        # Symbol class names (from training)
        self.class_names = self._load_class_names()

        # Initialize components
        self.symbol_model = None
        self.ocr_pipeline = get_ocr_pipeline()
        self.tag_associator = TagAssociator()

        # Load model if path provided
        if model_path and Path(model_path).exists():
            self._load_model(model_path)

    def _load_class_names(self) -> list[str]:
        """Load class names from symbol classes definition."""
        try:
            # Import from ml training module (dynamic import, path set at runtime)
            import sys
            sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "ml" / "training"))
            from symbol_classes import get_class_names  # type: ignore[import-not-found]
            class_names: list[str] = get_class_names()
            return ["__background__"] + class_names
        except ImportError:
            logger.warning("Could not load symbol classes, using placeholders")
            return ["__background__"] + [f"class_{i}" for i in range(50)]

    def _load_model(self, path: str) -> None:
        """Load the symbol detection model."""
        try:
            # Dynamic import from ml training module (path set at runtime)
            import sys
            sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "ml" / "training"))
            from model import SymbolDetector  # type: ignore[import-not-found]

            self.symbol_model = SymbolDetector.load(path, device=self.device)
            self.symbol_model.to(self.device)  # type: ignore[attr-defined]
            self.symbol_model.eval()  # type: ignore[attr-defined]
            logger.info(f"Loaded model from {path}")
        except Exception as e:
            logger.error(f"Failed to load model: {e}")
            self.symbol_model = None

    def analyze_image(self, image: Image.Image | bytes) -> AnalysisResult:
        """
        Analyze a P&ID image.

        Args:
            image: PIL Image or image bytes

        Returns:
            AnalysisResult with detected symbols, text, and associations
        """
        # Convert bytes to PIL Image if needed
        if isinstance(image, bytes):
            image = Image.open(io.BytesIO(image))

        # Ensure RGB
        if image.mode != "RGB":
            image = image.convert("RGB")

        width, height = image.size

        # Detect symbols
        symbols = self._detect_symbols(image)

        # Extract text with OCR
        texts = self.ocr_pipeline.extract_text(image)

        # Associate tags with symbols
        symbol_dicts = [
            {
                "bbox": (s.bbox[0], s.bbox[1], s.bbox[2], s.bbox[3]),
                "class_id": s.class_id,
                "class_name": s.class_name,
            }
            for s in symbols
        ]
        associations = self.tag_associator.associate(texts, symbol_dicts)

        # Update symbols with associated tags
        for assoc in associations:
            text = assoc["text"]
            for symbol in symbols:
                if (
                    symbol.class_id == assoc["symbol"]["class_id"]
                    and symbol.bbox == tuple(assoc["symbol"]["bbox"])
                ):
                    symbol.tag = text.normalized_tag or text.text
                    break

        return AnalysisResult(
            symbols=symbols,
            texts=texts,
            associations=associations,
            image_width=width,
            image_height=height,
        )

    def _detect_symbols(self, image: Image.Image) -> list[DetectedSymbol]:
        """Detect symbols in an image."""
        if self.symbol_model is None:
            logger.warning("Symbol model not loaded, returning empty results")
            return []

        try:
            # Convert to tensor (F is standard PyTorch convention for functional transforms)
            import torchvision.transforms.functional as F  # noqa: N812
            image_tensor = F.to_tensor(image).to(self.device)

            # Run inference
            with torch.no_grad():
                predictions = self.symbol_model.predict(image_tensor)

            symbols = []
            boxes = predictions["boxes"].cpu().numpy()
            labels = predictions["labels"].cpu().numpy()
            scores = predictions["scores"].cpu().numpy()

            for box, label, score in zip(boxes, labels, scores):
                if score >= self.confidence_threshold:
                    x1, y1, x2, y2 = box
                    symbols.append(
                        DetectedSymbol(
                            class_id=int(label),
                            class_name=self.class_names[int(label)],
                            confidence=float(score),
                            bbox=(float(x1), float(y1), float(x2 - x1), float(y2 - y1)),
                        )
                    )

            return symbols

        except Exception as e:
            logger.error(f"Symbol detection failed: {e}")
            return []

    def analyze_bytes(self, image_bytes: bytes) -> dict[str, object]:
        """
        Analyze image bytes and return JSON-serializable result.

        Args:
            image_bytes: Image as bytes

        Returns:
            Dict with analysis results
        """
        result = self.analyze_image(image_bytes)

        return {
            "symbols": [
                {
                    "class_id": s.class_id,
                    "class_name": s.class_name,
                    "confidence": s.confidence,
                    "bbox": {
                        "x": s.bbox[0],
                        "y": s.bbox[1],
                        "width": s.bbox[2],
                        "height": s.bbox[3],
                    },
                    "tag": s.tag,
                }
                for s in result.symbols
            ],
            "texts": [
                {
                    "text": t.text,
                    "confidence": t.confidence,
                    "bbox": {
                        "x": t.bbox[0],
                        "y": t.bbox[1],
                        "width": t.bbox[2],
                        "height": t.bbox[3],
                    },
                    "rotation": t.rotation,
                    "tag_type": t.tag_type.value,
                    "normalized_tag": t.normalized_tag,
                }
                for t in result.texts
            ],
            "image_size": {
                "width": result.image_width,
                "height": result.image_height,
            },
            "summary": {
                "total_symbols": len(result.symbols),
                "total_texts": len(result.texts),
                "tagged_symbols": sum(1 for s in result.symbols if s.tag),
            },
        }


# Singleton instance
_inference_service: InferenceService | None = None


def get_inference_service() -> InferenceService:
    """Get or create the inference service instance."""
    global _inference_service
    if _inference_service is None:
        _inference_service = InferenceService()
    return _inference_service

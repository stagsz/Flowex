import asyncio
import logging
from datetime import UTC, datetime
from io import BytesIO
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.celery_app import celery_app
from app.core.database import SessionLocal
from app.models import Drawing, DrawingStatus, FileType, Symbol, SymbolCategory, TextAnnotation
from app.services.pdf_processing import (
    PDFProcessingError,
    create_image_tiles,
    detect_pdf_type,
    get_pdf_metadata,
    pdf_to_images,
    preprocess_scanned_image,
)
from app.services.storage import get_storage_service

logger = logging.getLogger(__name__)


def _map_class_to_category(class_name: str) -> SymbolCategory:
    """Map symbol class name to SymbolCategory enum."""
    class_name_lower = class_name.lower()

    # Equipment patterns
    if any(kw in class_name_lower for kw in [
        "pump", "compressor", "vessel", "tank", "reactor", "exchanger",
        "heater", "cooler", "column", "separator", "filter", "blower", "fan"
    ]):
        return SymbolCategory.EQUIPMENT

    # Instrument patterns
    if any(kw in class_name_lower for kw in [
        "indicator", "transmitter", "controller", "recorder", "gauge",
        "sensor", "flow", "level", "pressure", "temperature"
    ]) or class_name_lower.startswith(("pt", "ft", "lt", "tt", "pi", "fi", "li", "ti")):
        return SymbolCategory.INSTRUMENT

    # Valve patterns
    if any(kw in class_name_lower for kw in [
        "valve", "gate", "globe", "ball", "check", "butterfly", "control"
    ]):
        return SymbolCategory.VALVE

    return SymbolCategory.OTHER


@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)  # type: ignore[untyped-decorator]
def process_drawing(self: Any, drawing_id: str) -> dict[str, Any]:
    """
    Process an uploaded PDF drawing.

    Steps:
    1. Download PDF from S3
    2. Detect PDF type (vector vs scanned)
    3. Convert to images
    4. Preprocess if scanned
    5. Create tiles for AI processing
    6. Store processed images
    7. Update drawing status

    Args:
        drawing_id: UUID of the drawing to process

    Returns:
        Dict with processing results
    """
    db: Session = SessionLocal()

    try:
        # Get drawing from database
        drawing = db.query(Drawing).filter(Drawing.id == UUID(drawing_id)).first()
        if not drawing:
            logger.error(f"Drawing not found: {drawing_id}")
            return {"error": "Drawing not found", "drawing_id": drawing_id}

        # Update status to processing
        drawing.status = DrawingStatus.processing
        drawing.processing_started_at = datetime.now(UTC)
        db.commit()

        logger.info(f"Starting processing for drawing {drawing_id}")

        # Download PDF from storage
        storage = get_storage_service()
        try:
            pdf_bytes = asyncio.run(storage.download_file(drawing.storage_path))
        except Exception as e:
            raise PDFProcessingError(f"Failed to download PDF: {e}") from e

        # Detect PDF type
        pdf_type = detect_pdf_type(pdf_bytes)
        drawing.file_type = FileType(pdf_type)
        logger.info(f"Detected PDF type: {pdf_type}")

        # Get metadata
        metadata = get_pdf_metadata(pdf_bytes)
        logger.info(f"PDF metadata: {metadata}")

        # Convert to images
        images = pdf_to_images(pdf_bytes)
        logger.info(f"Converted PDF to {len(images)} images")

        # Process each page
        processed_images = []
        all_tiles = []

        for i, image_bytes in enumerate(images):
            # Preprocess if scanned
            if pdf_type == "pdf_scanned":
                image_bytes = preprocess_scanned_image(image_bytes)
                logger.debug(f"Preprocessed page {i + 1}")

            processed_images.append(image_bytes)

            # Create tiles for AI processing
            tiles = create_image_tiles(image_bytes)
            all_tiles.extend([(i, t) for t in tiles])
            logger.debug(f"Created {len(tiles)} tiles for page {i + 1}")

        # Store processed images (optional - for debugging/review)
        base_path = drawing.storage_path.rsplit("/", 1)[0]
        for i, img_bytes in enumerate(processed_images):
            img_path = f"{base_path}/processed/page_{i + 1}.png"
            asyncio.run(storage.upload_file(BytesIO(img_bytes), img_path, "image/png"))

        # Run AI inference on processed images
        logger.info(f"Running AI inference for drawing {drawing_id}")
        total_symbols = 0
        total_texts = 0

        try:
            from app.ml.inference import get_inference_service

            inference_service = get_inference_service()

            # Process each page
            for page_idx, img_bytes in enumerate(processed_images):
                analysis = inference_service.analyze_image(img_bytes)

                # Store detected symbols
                for detected in analysis.symbols:
                    symbol = Symbol(
                        drawing_id=drawing.id,
                        symbol_class=detected.class_name,
                        category=_map_class_to_category(detected.class_name),
                        tag_number=detected.tag,
                        bbox_x=detected.bbox[0],
                        bbox_y=detected.bbox[1],
                        bbox_width=detected.bbox[2],
                        bbox_height=detected.bbox[3],
                        confidence=detected.confidence,
                        is_verified=False,
                        is_deleted=False,
                    )
                    db.add(symbol)
                    total_symbols += 1

                # Store detected text annotations
                for text in analysis.texts:
                    annotation = TextAnnotation(
                        drawing_id=drawing.id,
                        text_content=text.text,
                        bbox_x=text.bbox[0],
                        bbox_y=text.bbox[1],
                        bbox_width=text.bbox[2],
                        bbox_height=text.bbox[3],
                        rotation=text.rotation,
                        confidence=text.confidence,
                        is_verified=False,
                        is_deleted=False,
                    )
                    db.add(annotation)
                    total_texts += 1

                logger.info(
                    f"Page {page_idx + 1}: detected {len(analysis.symbols)} symbols, "
                    f"{len(analysis.texts)} texts"
                )

            db.commit()
            logger.info(
                f"Stored {total_symbols} symbols and {total_texts} texts for drawing {drawing_id}"
            )

        except Exception as e:
            logger.warning(f"AI inference failed for {drawing_id}: {e}. Continuing with manual review.")
            # Don't fail the entire task if AI inference fails
            # The drawing will still be in REVIEW status for manual annotation

        # Update drawing status to review (ready for validation)
        drawing.status = DrawingStatus.review
        drawing.processing_completed_at = datetime.now(UTC)
        db.commit()

        result = {
            "drawing_id": drawing_id,
            "status": "success",
            "pdf_type": pdf_type,
            "page_count": len(images),
            "total_tiles": len(all_tiles),
            "total_symbols": total_symbols,
            "total_texts": total_texts,
            "metadata": metadata,
        }

        logger.info(f"Successfully processed drawing {drawing_id}: {result}")
        return result

    except PDFProcessingError as e:
        logger.error(f"PDF processing error for {drawing_id}: {e}")
        if drawing is not None:
            drawing.status = DrawingStatus.error
            drawing.error_message = str(e)
            db.commit()

        # Retry on transient errors
        raise self.retry(exc=e)

    except Exception as e:
        logger.error(f"Unexpected error processing {drawing_id}: {e}")
        if drawing is not None:
            drawing.status = DrawingStatus.error
            drawing.error_message = f"Unexpected error: {e}"
            db.commit()
        return {"error": str(e), "drawing_id": drawing_id}

    finally:
        db.close()


@celery_app.task  # type: ignore[untyped-decorator]
def check_processing_health() -> dict[str, str]:
    """Health check task to verify Celery is working."""
    return {"status": "healthy", "worker": "celery"}

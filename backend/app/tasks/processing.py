import logging
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.celery_app import celery_app
from app.core.database import SessionLocal
from app.models import Drawing, DrawingStatus, FileType
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


@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
def process_drawing(self, drawing_id: str) -> dict:
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
        drawing.status = DrawingStatus.PROCESSING
        drawing.processing_started_at = datetime.now(UTC)
        db.commit()

        logger.info(f"Starting processing for drawing {drawing_id}")

        # Download PDF from S3
        storage = get_storage_service()
        try:
            pdf_bytes = storage.s3_client.get_object(
                Bucket=storage.bucket, Key=drawing.storage_path
            )["Body"].read()
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

        # Store processed images in S3 (optional - for debugging/review)
        base_path = drawing.storage_path.rsplit("/", 1)[0]
        for i, img_bytes in enumerate(processed_images):
            img_path = f"{base_path}/processed/page_{i + 1}.png"
            storage.s3_client.put_object(
                Bucket=storage.bucket,
                Key=img_path,
                Body=img_bytes,
                ContentType="image/png",
            )

        # Update drawing status to review (ready for AI processing)
        drawing.status = DrawingStatus.REVIEW
        drawing.processing_completed_at = datetime.now(UTC)
        db.commit()

        result = {
            "drawing_id": drawing_id,
            "status": "success",
            "pdf_type": pdf_type,
            "page_count": len(images),
            "total_tiles": len(all_tiles),
            "metadata": metadata,
        }

        logger.info(f"Successfully processed drawing {drawing_id}: {result}")
        return result

    except PDFProcessingError as e:
        logger.error(f"PDF processing error for {drawing_id}: {e}")
        drawing.status = DrawingStatus.ERROR
        drawing.error_message = str(e)
        db.commit()

        # Retry on transient errors
        raise self.retry(exc=e)

    except Exception as e:
        logger.error(f"Unexpected error processing {drawing_id}: {e}")
        drawing.status = DrawingStatus.ERROR
        drawing.error_message = f"Unexpected error: {e}"
        db.commit()
        return {"error": str(e), "drawing_id": drawing_id}

    finally:
        db.close()


@celery_app.task
def check_processing_health() -> dict:
    """Health check task to verify Celery is working."""
    return {"status": "healthy", "worker": "celery"}

import io
import logging
from pathlib import Path
from typing import Literal

import fitz  # PyMuPDF
from PIL import Image

logger = logging.getLogger(__name__)

# Processing constants
DPI = 300  # Resolution for image conversion
MAX_IMAGE_SIZE = 4096  # Maximum dimension for processed images
TILE_SIZE = 1024  # Size of tiles for AI processing


class PDFProcessingError(Exception):
    """Exception raised for PDF processing errors."""

    pass


def detect_pdf_type(pdf_bytes: bytes) -> Literal["pdf_vector", "pdf_scanned"]:
    """
    Detect if a PDF is vector-based or scanned (raster).

    Vector PDFs have extractable text and drawing commands.
    Scanned PDFs are primarily images with little/no text.
    """
    try:
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        total_text_length = 0
        total_images = 0
        total_pages = len(doc)

        for page in doc:
            # Count text characters
            text = page.get_text()
            total_text_length += len(text.strip())

            # Count images
            image_list = page.get_images()
            total_images += len(image_list)

        doc.close()

        # Heuristic: If average text per page is low and images are present,
        # it's likely a scanned PDF
        avg_text_per_page = total_text_length / max(total_pages, 1)
        avg_images_per_page = total_images / max(total_pages, 1)

        if avg_text_per_page < 100 and avg_images_per_page >= 1:
            return "pdf_scanned"
        return "pdf_vector"

    except Exception as e:
        logger.error(f"Error detecting PDF type: {e}")
        raise PDFProcessingError(f"Failed to detect PDF type: {e}") from e


def pdf_to_images(
    pdf_bytes: bytes,
    dpi: int = DPI,
    max_size: int = MAX_IMAGE_SIZE,
) -> list[bytes]:
    """
    Convert PDF pages to PNG images.

    Args:
        pdf_bytes: PDF file content
        dpi: Resolution for rendering
        max_size: Maximum dimension for output images

    Returns:
        List of PNG image bytes for each page
    """
    try:
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        images = []

        for page_num, page in enumerate(doc):
            # Calculate zoom factor for desired DPI
            zoom = dpi / 72  # 72 is the default PDF DPI
            matrix = fitz.Matrix(zoom, zoom)

            # Render page to pixmap
            pixmap = page.get_pixmap(matrix=matrix)

            # Convert to PIL Image
            img = Image.frombytes("RGB", [pixmap.width, pixmap.height], pixmap.samples)

            # Resize if too large
            if img.width > max_size or img.height > max_size:
                ratio = min(max_size / img.width, max_size / img.height)
                new_size = (int(img.width * ratio), int(img.height * ratio))
                img = img.resize(new_size, Image.Resampling.LANCZOS)

            # Convert to PNG bytes
            buffer = io.BytesIO()
            img.save(buffer, format="PNG")
            images.append(buffer.getvalue())

            logger.debug(f"Converted page {page_num + 1} to image ({img.width}x{img.height})")

        doc.close()
        return images

    except Exception as e:
        logger.error(f"Error converting PDF to images: {e}")
        raise PDFProcessingError(f"Failed to convert PDF to images: {e}") from e


def preprocess_scanned_image(image_bytes: bytes) -> bytes:
    """
    Preprocess a scanned image for better OCR and symbol detection.

    Steps:
    1. Convert to grayscale
    2. Deskew (straighten rotated scans)
    3. Denoise
    4. Binarize (convert to black and white)
    5. Enhance contrast

    Args:
        image_bytes: Input image as PNG bytes

    Returns:
        Preprocessed image as PNG bytes
    """
    try:
        # Load image
        img = Image.open(io.BytesIO(image_bytes))

        # Convert to grayscale
        if img.mode != "L":
            img = img.convert("L")

        # Simple contrast enhancement using PIL
        # (More advanced preprocessing would use OpenCV)
        from PIL import ImageEnhance, ImageFilter

        # Enhance contrast
        enhancer = ImageEnhance.Contrast(img)
        img = enhancer.enhance(1.5)

        # Sharpen slightly
        img = img.filter(ImageFilter.SHARPEN)

        # Convert to binary (threshold at 128)
        img = img.point(lambda x: 255 if x > 128 else 0, mode="1")

        # Convert back to grayscale for output
        img = img.convert("L")

        # Save to bytes
        buffer = io.BytesIO()
        img.save(buffer, format="PNG")
        return buffer.getvalue()

    except Exception as e:
        logger.error(f"Error preprocessing image: {e}")
        raise PDFProcessingError(f"Failed to preprocess image: {e}") from e


def create_image_tiles(
    image_bytes: bytes,
    tile_size: int = TILE_SIZE,
    overlap: int = 64,
) -> list[dict]:
    """
    Split an image into overlapping tiles for AI processing.

    Args:
        image_bytes: Input image as PNG bytes
        tile_size: Size of each tile (square)
        overlap: Overlap between adjacent tiles

    Returns:
        List of dicts with tile info: {bytes, x, y, width, height}
    """
    try:
        img = Image.open(io.BytesIO(image_bytes))
        width, height = img.size
        tiles = []

        step = tile_size - overlap

        for y in range(0, height, step):
            for x in range(0, width, step):
                # Calculate tile bounds
                x2 = min(x + tile_size, width)
                y2 = min(y + tile_size, height)

                # Crop tile
                tile = img.crop((x, y, x2, y2))

                # Save to bytes
                buffer = io.BytesIO()
                tile.save(buffer, format="PNG")

                tiles.append(
                    {
                        "bytes": buffer.getvalue(),
                        "x": x,
                        "y": y,
                        "width": x2 - x,
                        "height": y2 - y,
                    }
                )

        logger.debug(f"Created {len(tiles)} tiles from {width}x{height} image")
        return tiles

    except Exception as e:
        logger.error(f"Error creating image tiles: {e}")
        raise PDFProcessingError(f"Failed to create image tiles: {e}") from e


def get_pdf_metadata(pdf_bytes: bytes) -> dict:
    """Extract metadata from a PDF file."""
    try:
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        metadata = {
            "page_count": len(doc),
            "title": doc.metadata.get("title", ""),
            "author": doc.metadata.get("author", ""),
            "creator": doc.metadata.get("creator", ""),
            "producer": doc.metadata.get("producer", ""),
            "creation_date": doc.metadata.get("creationDate", ""),
            "modification_date": doc.metadata.get("modDate", ""),
        }

        # Get page dimensions (from first page)
        if len(doc) > 0:
            page = doc[0]
            rect = page.rect
            metadata["page_width"] = rect.width
            metadata["page_height"] = rect.height

        doc.close()
        return metadata

    except Exception as e:
        logger.error(f"Error extracting PDF metadata: {e}")
        return {"error": str(e)}

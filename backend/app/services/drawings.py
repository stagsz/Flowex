import uuid
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.models import Drawing, DrawingStatus, Project
from app.services.storage import StorageError, get_storage_service

# File validation constants
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB
ALLOWED_CONTENT_TYPES = ["application/pdf"]
ALLOWED_EXTENSIONS = [".pdf"]


class FileValidationError(Exception):
    """Exception raised for file validation errors."""

    pass


def validate_file(filename: str, content_type: str, file_size: int) -> None:
    """Validate file type and size."""
    # Check file extension
    ext = "." + filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if ext not in ALLOWED_EXTENSIONS:
        raise FileValidationError(
            f"Invalid file type. Allowed extensions: {', '.join(ALLOWED_EXTENSIONS)}"
        )

    # Check content type
    if content_type not in ALLOWED_CONTENT_TYPES:
        raise FileValidationError(
            f"Invalid content type. Allowed types: {', '.join(ALLOWED_CONTENT_TYPES)}"
        )

    # Check file size
    if file_size > MAX_FILE_SIZE:
        raise FileValidationError(
            f"File too large. Maximum size: {MAX_FILE_SIZE // (1024 * 1024)}MB"
        )


async def create_drawing(
    db: Session,
    project_id: uuid.UUID,
    organization_id: uuid.UUID,
    filename: str,
    content_type: str,
    file_size: int,
    file_content: bytes,
) -> Drawing:
    """Create a new drawing with file upload to S3."""
    # Validate project exists and belongs to organization
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise ValueError("Project not found")
    if project.organization_id != organization_id:
        raise PermissionError("Access denied to this project")

    # Validate file
    validate_file(filename, content_type, file_size)

    # Upload to S3
    storage = get_storage_service()
    storage_path = storage.generate_storage_path(organization_id, filename)

    try:
        from io import BytesIO

        file_obj = BytesIO(file_content)
        await storage.upload_file(file_obj, storage_path, content_type)
    except StorageError as e:
        raise ValueError(f"Failed to upload file: {e}") from e

    # Create drawing record
    drawing = Drawing(
        project_id=project_id,
        original_filename=filename,
        storage_path=storage_path,
        file_size_bytes=file_size,
        status=DrawingStatus.uploaded,
    )
    db.add(drawing)
    db.commit()
    db.refresh(drawing)

    return drawing


async def get_drawing(db: Session, drawing_id: uuid.UUID) -> Drawing | None:
    """Get a drawing by ID."""
    return db.query(Drawing).filter(Drawing.id == drawing_id).first()


async def get_drawings_by_project(
    db: Session, project_id: uuid.UUID, skip: int = 0, limit: int = 100
) -> list[Drawing]:
    """Get all drawings for a project."""
    return (
        db.query(Drawing)
        .filter(Drawing.project_id == project_id)
        .order_by(Drawing.created_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )


async def delete_drawing(db: Session, drawing: Drawing) -> None:
    """Delete a drawing and its file from S3."""
    # Delete from S3
    storage = get_storage_service()
    try:
        await storage.delete_file(drawing.storage_path)
    except StorageError:
        pass  # Continue even if S3 deletion fails

    # Delete from database
    db.delete(drawing)
    db.commit()


async def update_drawing_status(
    db: Session, drawing: Drawing, status: DrawingStatus, error_message: str | None = None
) -> Drawing:
    """Update the status of a drawing."""
    drawing.status = status
    drawing.error_message = error_message

    if status == DrawingStatus.processing:
        drawing.processing_started_at = datetime.now(UTC)
    elif status in [DrawingStatus.review, DrawingStatus.complete, DrawingStatus.error]:
        drawing.processing_completed_at = datetime.now(UTC)

    db.commit()
    db.refresh(drawing)
    return drawing


async def get_download_url(drawing: Drawing, expires_in: int = 3600) -> str:
    """Get a presigned URL for downloading a drawing."""
    storage = get_storage_service()
    return await storage.get_presigned_url(drawing.storage_path, expires_in)

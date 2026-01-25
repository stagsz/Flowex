from datetime import UTC, datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile, status
from fastapi.responses import Response
from pydantic import BaseModel, ConfigDict
from sqlalchemy import Integer
from sqlalchemy.orm import Session

from app.core.config import StorageProvider, settings
from app.core.deps import get_current_user, get_db
from app.models import Drawing, DrawingStatus, Line, Project, Symbol, TextAnnotation, User
from app.models.symbol import SymbolCategory
from app.services import drawings as drawing_service
from app.services.drawings import FileValidationError
from app.services.storage import get_storage_service

router = APIRouter(prefix="/drawings", tags=["drawings"])


def _update_last_accessed(db: Session, drawing: Drawing) -> None:
    """Update the last_accessed_at timestamp for data retention tracking (GDPR-08)."""
    drawing.last_accessed_at = datetime.now(UTC)
    db.commit()


def calculate_progress_percentage(
    status: DrawingStatus,
    total_symbols: int = 0,
    verified_symbols: int = 0,
) -> int:
    """
    Calculate progress percentage based on drawing status and verification progress.

    Progress mapping:
    - uploaded: 0% (no processing started)
    - processing: 50% (processing in progress)
    - review: 80% + 20% * (verified_symbols / total_symbols) (verification progress)
    - complete: 100% (all done)
    - error: 0% (failed)

    For review status, shows actual verification progress from 80% to 100%.
    """
    if status == DrawingStatus.complete:
        return 100
    elif status == DrawingStatus.error:
        return 0
    elif status == DrawingStatus.uploaded:
        return 0
    elif status == DrawingStatus.processing:
        return 50
    elif status == DrawingStatus.review:
        # Calculate verification progress (80-100%)
        if total_symbols == 0:
            return 80  # No symbols to verify, show base progress
        verification_ratio = verified_symbols / total_symbols
        return min(100, 80 + int(20 * verification_ratio))
    else:
        return 0


class DrawingResponse(BaseModel):
    id: str
    project_id: str
    original_filename: str
    file_size_bytes: int
    file_type: str | None
    status: str
    error_message: str | None
    created_at: str
    updated_at: str
    processing_started_at: str | None
    processing_completed_at: str | None
    progress_percentage: int  # 0-100, calculated from status and verification progress

    model_config = ConfigDict(from_attributes=True)


class DrawingWithUrlResponse(DrawingResponse):
    download_url: str | None = None


class UploadUrlResponse(BaseModel):
    drawing_id: str
    upload_url: str
    storage_path: str


@router.post(
    "/upload/{project_id}",
    response_model=DrawingResponse,
    status_code=status.HTTP_201_CREATED,
)
async def upload_drawing(
    project_id: UUID,
    file: Annotated[UploadFile, File(description="PDF file to upload")],
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> DrawingResponse:
    """Upload a new P&ID drawing (PDF file)."""
    # Check project access
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    if project.organization_id != current_user.organization_id:
        raise HTTPException(status_code=403, detail="Access denied")

    # Read file content
    content = await file.read()
    file_size = len(content)

    try:
        drawing = await drawing_service.create_drawing(
            db=db,
            project_id=project_id,
            organization_id=current_user.organization_id,
            filename=file.filename or "unnamed.pdf",
            content_type=file.content_type or "application/pdf",
            file_size=file_size,
            file_content=content,
        )
    except FileValidationError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e)) from e

    return DrawingResponse(
        id=str(drawing.id),
        project_id=str(drawing.project_id),
        original_filename=drawing.original_filename,
        file_size_bytes=drawing.file_size_bytes,
        file_type=drawing.file_type.value if drawing.file_type else None,
        status=drawing.status.value,
        error_message=drawing.error_message,
        created_at=drawing.created_at.isoformat(),
        updated_at=drawing.updated_at.isoformat(),
        processing_started_at=(
            drawing.processing_started_at.isoformat() if drawing.processing_started_at else None
        ),
        processing_completed_at=(
            drawing.processing_completed_at.isoformat()
            if drawing.processing_completed_at
            else None
        ),
        progress_percentage=calculate_progress_percentage(drawing.status),
    )


@router.get("/project/{project_id}", response_model=list[DrawingResponse])
async def list_drawings(
    project_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    skip: int = 0,
    limit: int = 100,
) -> list[DrawingResponse]:
    """List all drawings for a project with progress percentage."""
    from sqlalchemy import func

    # Check project access
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    if project.organization_id != current_user.organization_id:
        raise HTTPException(status_code=403, detail="Access denied")

    drawings = await drawing_service.get_drawings_by_project(db, project_id, skip, limit)

    # Get symbol verification stats for drawings in review status (efficient batch query)
    review_drawing_ids = [d.id for d in drawings if d.status == DrawingStatus.review]
    symbol_stats: dict[UUID, tuple[int, int]] = {}  # {drawing_id: (total, verified)}

    if review_drawing_ids:
        # Batch query for symbol counts per drawing
        stats_query = (
            db.query(
                Symbol.drawing_id,
                func.count(Symbol.id).label("total"),
                func.sum(func.cast(Symbol.is_verified, Integer)).label("verified"),
            )
            .filter(
                Symbol.drawing_id.in_(review_drawing_ids),
                Symbol.is_deleted == False,  # noqa: E712
            )
            .group_by(Symbol.drawing_id)
            .all()
        )
        for row in stats_query:
            symbol_stats[row.drawing_id] = (row.total, row.verified or 0)

    return [
        DrawingResponse(
            id=str(d.id),
            project_id=str(d.project_id),
            original_filename=d.original_filename,
            file_size_bytes=d.file_size_bytes,
            file_type=d.file_type.value if d.file_type else None,
            status=d.status.value,
            error_message=d.error_message,
            created_at=d.created_at.isoformat(),
            updated_at=d.updated_at.isoformat(),
            processing_started_at=(
                d.processing_started_at.isoformat() if d.processing_started_at else None
            ),
            processing_completed_at=(
                d.processing_completed_at.isoformat() if d.processing_completed_at else None
            ),
            progress_percentage=calculate_progress_percentage(
                d.status,
                total_symbols=symbol_stats.get(d.id, (0, 0))[0],
                verified_symbols=symbol_stats.get(d.id, (0, 0))[1],
            ),
        )
        for d in drawings
    ]


@router.get("/{drawing_id}", response_model=DrawingWithUrlResponse)
async def get_drawing(
    drawing_id: UUID,
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> DrawingWithUrlResponse:
    """Get a drawing by ID with download URL and progress percentage."""
    from sqlalchemy import func

    drawing = await drawing_service.get_drawing(db, drawing_id)
    if not drawing:
        raise HTTPException(status_code=404, detail="Drawing not found")

    # Check project access
    project = db.query(Project).filter(Project.id == drawing.project_id).first()
    if not project or project.organization_id != current_user.organization_id:
        raise HTTPException(status_code=403, detail="Access denied")

    # Update last access time for retention tracking (GDPR-08)
    _update_last_accessed(db, drawing)

    # Get download URL - use API endpoint for local storage
    try:
        if settings.STORAGE_PROVIDER == StorageProvider.LOCAL:
            # For local storage, use the API download endpoint
            base_url = str(request.base_url).rstrip("/")
            download_url = f"{base_url}/api/v1/drawings/{drawing_id}/download"
        else:
            download_url = await drawing_service.get_download_url(drawing)
    except Exception:
        download_url = None

    # Calculate progress based on verification status
    total_symbols = 0
    verified_symbols = 0
    if drawing.status == DrawingStatus.review:
        stats = db.query(
            func.count(Symbol.id).label("total"),
            func.sum(func.cast(Symbol.is_verified, Integer)).label("verified"),
        ).filter(
            Symbol.drawing_id == drawing_id,
            Symbol.is_deleted == False,  # noqa: E712
        ).first()
        if stats:
            total_symbols = stats.total or 0
            verified_symbols = stats.verified or 0

    return DrawingWithUrlResponse(
        id=str(drawing.id),
        project_id=str(drawing.project_id),
        original_filename=drawing.original_filename,
        file_size_bytes=drawing.file_size_bytes,
        file_type=drawing.file_type.value if drawing.file_type else None,
        status=drawing.status.value,
        error_message=drawing.error_message,
        created_at=drawing.created_at.isoformat(),
        updated_at=drawing.updated_at.isoformat(),
        processing_started_at=(
            drawing.processing_started_at.isoformat() if drawing.processing_started_at else None
        ),
        processing_completed_at=(
            drawing.processing_completed_at.isoformat()
            if drawing.processing_completed_at
            else None
        ),
        download_url=download_url,
        progress_percentage=calculate_progress_percentage(
            drawing.status,
            total_symbols=total_symbols,
            verified_symbols=verified_symbols,
        ),
    )


@router.get("/{drawing_id}/download")
async def download_drawing(
    drawing_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> Response:
    """Download the original PDF file for a drawing."""
    drawing = await drawing_service.get_drawing(db, drawing_id)
    if not drawing:
        raise HTTPException(status_code=404, detail="Drawing not found")

    # Check project access
    project = db.query(Project).filter(Project.id == drawing.project_id).first()
    if not project or project.organization_id != current_user.organization_id:
        raise HTTPException(status_code=403, detail="Access denied")

    # Update last access time for retention tracking (GDPR-08)
    _update_last_accessed(db, drawing)

    # Download file from storage
    try:
        storage = get_storage_service()
        file_content = await storage.download_file(drawing.storage_path)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="File not found in storage")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to download file: {e}")

    return Response(
        content=file_content,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'inline; filename="{drawing.original_filename}"',
        },
    )


@router.delete("/{drawing_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_drawing(
    drawing_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> None:
    """Delete a drawing."""
    drawing = await drawing_service.get_drawing(db, drawing_id)
    if not drawing:
        raise HTTPException(status_code=404, detail="Drawing not found")

    # Check project access
    project = db.query(Project).filter(Project.id == drawing.project_id).first()
    if not project or project.organization_id != current_user.organization_id:
        raise HTTPException(status_code=403, detail="Access denied")

    await drawing_service.delete_drawing(db, drawing)


class CancelResponse(BaseModel):
    """Response for cancel operation."""

    drawing_id: str
    status: str
    message: str


@router.delete("/{drawing_id}/cancel", response_model=CancelResponse)
async def cancel_upload(
    drawing_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> CancelResponse:
    """
    Cancel an in-progress upload and cleanup resources.

    This endpoint is called when a user cancels an upload mid-flight.
    It deletes the partially uploaded file from storage and removes
    the drawing record from the database.

    Can only cancel drawings in 'uploaded' or 'processing' status.
    """
    drawing = await drawing_service.get_drawing(db, drawing_id)
    if not drawing:
        # Drawing doesn't exist - possibly already cleaned up or never created
        # Return success to be idempotent for the frontend
        return CancelResponse(
            drawing_id=str(drawing_id),
            status="not_found",
            message="Drawing not found (may have already been cancelled)",
        )

    # Check project access
    project = db.query(Project).filter(Project.id == drawing.project_id).first()
    if not project or project.organization_id != current_user.organization_id:
        raise HTTPException(status_code=403, detail="Access denied")

    # Only allow cancellation of uploads that are in progress or just uploaded
    cancellable_statuses = [DrawingStatus.uploaded, DrawingStatus.processing]
    if drawing.status not in cancellable_statuses:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot cancel drawing with status '{drawing.status.value}'. "
            f"Only drawings with status 'uploaded' or 'processing' can be cancelled.",
        )

    # Delete the drawing (this also cleans up the file in storage)
    await drawing_service.delete_drawing(db, drawing)

    return CancelResponse(
        drawing_id=str(drawing_id),
        status="cancelled",
        message="Upload cancelled and resources cleaned up",
    )


class ProcessingResponse(BaseModel):
    drawing_id: str
    task_id: str
    status: str
    message: str


@router.post("/{drawing_id}/process", response_model=ProcessingResponse)
async def start_processing(
    drawing_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> ProcessingResponse:
    """Start processing a drawing (PDF to images, preprocessing)."""
    drawing = await drawing_service.get_drawing(db, drawing_id)
    if not drawing:
        raise HTTPException(status_code=404, detail="Drawing not found")

    # Check project access
    project = db.query(Project).filter(Project.id == drawing.project_id).first()
    if not project or project.organization_id != current_user.organization_id:
        raise HTTPException(status_code=403, detail="Access denied")

    # Check if already processing or complete
    if drawing.status == DrawingStatus.processing:
        raise HTTPException(status_code=400, detail="Drawing is already being processed")
    if drawing.status == DrawingStatus.complete:
        raise HTTPException(status_code=400, detail="Drawing has already been processed")

    # Queue the processing task
    from app.tasks.processing import process_drawing

    try:
        task = process_drawing.delay(str(drawing_id))
        # In eager mode, task.id might be None and task already ran
        task_id = task.id if task.id else "eager-mode"
        return ProcessingResponse(
            drawing_id=str(drawing_id),
            task_id=task_id,
            status="queued",
            message="Processing task has been queued",
        )
    except Exception as e:
        # Task failed - log full traceback and return error
        import logging
        import traceback
        logger = logging.getLogger(__name__)
        logger.error(f"Failed to process drawing: {e}\n{traceback.format_exc()}")

        # Update drawing status to error
        if drawing:
            drawing.status = DrawingStatus.error
            drawing.error_message = str(e)[:500]  # Truncate long errors
            db.commit()

        raise HTTPException(
            status_code=500,
            detail=f"Processing failed: {str(e)}"
        )


@router.get("/{drawing_id}/process/status")
async def get_processing_status(
    drawing_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> dict[str, str | None]:
    """Get the processing status of a drawing."""
    drawing = await drawing_service.get_drawing(db, drawing_id)
    if not drawing:
        raise HTTPException(status_code=404, detail="Drawing not found")

    # Check project access
    project = db.query(Project).filter(Project.id == drawing.project_id).first()
    if not project or project.organization_id != current_user.organization_id:
        raise HTTPException(status_code=403, detail="Access denied")

    return {
        "drawing_id": str(drawing_id),
        "status": drawing.status.value,
        "file_type": drawing.file_type.value if drawing.file_type else None,
        "error_message": drawing.error_message,
        "processing_started_at": (
            drawing.processing_started_at.isoformat() if drawing.processing_started_at else None
        ),
        "processing_completed_at": (
            drawing.processing_completed_at.isoformat()
            if drawing.processing_completed_at
            else None
        ),
    }


# Symbol response models
class SymbolResponse(BaseModel):
    id: str
    symbol_class: str
    category: str
    tag_number: str | None
    bbox_x: float
    bbox_y: float
    bbox_width: float
    bbox_height: float
    confidence: float | None
    is_verified: bool
    is_flagged: bool

    model_config = ConfigDict(from_attributes=True)


class TextAnnotationResponse(BaseModel):
    id: str
    text_content: str
    bbox_x: float
    bbox_y: float
    bbox_width: float
    bbox_height: float
    rotation: int
    confidence: float | None
    is_verified: bool
    associated_symbol_id: str | None

    model_config = ConfigDict(from_attributes=True)


class SymbolsAndTextsResponse(BaseModel):
    symbols: list[SymbolResponse]
    texts: list[TextAnnotationResponse]
    summary: dict[str, int]


class SymbolCreateRequest(BaseModel):
    symbol_class: str
    category: str
    tag_number: str | None = None
    bbox_x: float
    bbox_y: float
    bbox_width: float
    bbox_height: float
    confidence: float | None = None
    is_verified: bool = False


class SymbolUpdateRequest(BaseModel):
    tag_number: str | None = None
    symbol_class: str | None = None
    is_verified: bool | None = None
    is_flagged: bool | None = None


class TextUpdateRequest(BaseModel):
    text_content: str | None = None
    is_verified: bool | None = None


@router.get("/{drawing_id}/symbols", response_model=SymbolsAndTextsResponse)
async def get_drawing_symbols(
    drawing_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    include_deleted: bool = False,
) -> SymbolsAndTextsResponse:
    """Get all detected symbols and text annotations for a drawing."""
    drawing = await drawing_service.get_drawing(db, drawing_id)
    if not drawing:
        raise HTTPException(status_code=404, detail="Drawing not found")

    # Check project access
    project = db.query(Project).filter(Project.id == drawing.project_id).first()
    if not project or project.organization_id != current_user.organization_id:
        raise HTTPException(status_code=403, detail="Access denied")

    # Get symbols
    symbols_query = db.query(Symbol).filter(Symbol.drawing_id == drawing_id)
    if not include_deleted:
        symbols_query = symbols_query.filter(Symbol.is_deleted == False)  # noqa: E712
    symbols = symbols_query.order_by(Symbol.created_at).all()

    # Get text annotations
    texts_query = db.query(TextAnnotation).filter(TextAnnotation.drawing_id == drawing_id)
    if not include_deleted:
        texts_query = texts_query.filter(TextAnnotation.is_deleted == False)  # noqa: E712
    texts = texts_query.order_by(TextAnnotation.created_at).all()

    # Build response
    symbol_responses = [
        SymbolResponse(
            id=str(s.id),
            symbol_class=s.symbol_class,
            category=s.category.value,
            tag_number=s.tag_number,
            bbox_x=s.bbox_x,
            bbox_y=s.bbox_y,
            bbox_width=s.bbox_width,
            bbox_height=s.bbox_height,
            confidence=s.confidence,
            is_verified=s.is_verified,
            is_flagged=s.is_flagged,
        )
        for s in symbols
    ]

    text_responses = [
        TextAnnotationResponse(
            id=str(t.id),
            text_content=t.text_content,
            bbox_x=t.bbox_x,
            bbox_y=t.bbox_y,
            bbox_width=t.bbox_width,
            bbox_height=t.bbox_height,
            rotation=t.rotation,
            confidence=t.confidence,
            is_verified=t.is_verified,
            associated_symbol_id=str(t.associated_symbol_id) if t.associated_symbol_id else None,
        )
        for t in texts
    ]

    # Summary stats
    verified_symbols = sum(1 for s in symbols if s.is_verified)
    flagged_symbols = sum(1 for s in symbols if s.is_flagged)
    low_confidence_symbols = sum(1 for s in symbols if s.confidence and s.confidence < 0.85)

    return SymbolsAndTextsResponse(
        symbols=symbol_responses,
        texts=text_responses,
        summary={
            "total_symbols": len(symbols),
            "verified_symbols": verified_symbols,
            "flagged_symbols": flagged_symbols,
            "low_confidence_symbols": low_confidence_symbols,
            "total_texts": len(texts),
            "verified_texts": sum(1 for t in texts if t.is_verified),
        },
    )


@router.post("/{drawing_id}/symbols", response_model=SymbolResponse, status_code=201)
async def create_symbol(
    drawing_id: UUID,
    symbol_data: SymbolCreateRequest,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> SymbolResponse:
    """Create a new symbol (manually add a missing symbol)."""
    drawing = await drawing_service.get_drawing(db, drawing_id)
    if not drawing:
        raise HTTPException(status_code=404, detail="Drawing not found")

    # Check project access
    project = db.query(Project).filter(Project.id == drawing.project_id).first()
    if not project or project.organization_id != current_user.organization_id:
        raise HTTPException(status_code=403, detail="Access denied")

    # Map category string to enum
    try:
        category = SymbolCategory(symbol_data.category.lower())
    except ValueError:
        category = SymbolCategory.OTHER

    # Create new symbol
    symbol = Symbol(
        drawing_id=drawing_id,
        symbol_class=symbol_data.symbol_class,
        category=category,
        tag_number=symbol_data.tag_number,
        bbox_x=symbol_data.bbox_x,
        bbox_y=symbol_data.bbox_y,
        bbox_width=symbol_data.bbox_width,
        bbox_height=symbol_data.bbox_height,
        confidence=symbol_data.confidence,
        is_verified=symbol_data.is_verified,
    )

    db.add(symbol)
    db.commit()
    db.refresh(symbol)

    return SymbolResponse(
        id=str(symbol.id),
        symbol_class=symbol.symbol_class,
        category=symbol.category.value,
        tag_number=symbol.tag_number,
        bbox_x=symbol.bbox_x,
        bbox_y=symbol.bbox_y,
        bbox_width=symbol.bbox_width,
        bbox_height=symbol.bbox_height,
        confidence=symbol.confidence,
        is_verified=symbol.is_verified,
        is_flagged=symbol.is_flagged,
    )


@router.patch("/{drawing_id}/symbols/{symbol_id}", response_model=SymbolResponse)
async def update_symbol(
    drawing_id: UUID,
    symbol_id: UUID,
    update: SymbolUpdateRequest,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> SymbolResponse:
    """Update a symbol's tag, class, or verification status."""
    drawing = await drawing_service.get_drawing(db, drawing_id)
    if not drawing:
        raise HTTPException(status_code=404, detail="Drawing not found")

    # Check project access
    project = db.query(Project).filter(Project.id == drawing.project_id).first()
    if not project or project.organization_id != current_user.organization_id:
        raise HTTPException(status_code=403, detail="Access denied")

    # Get symbol
    symbol = db.query(Symbol).filter(
        Symbol.id == symbol_id,
        Symbol.drawing_id == drawing_id,
    ).first()
    if not symbol:
        raise HTTPException(status_code=404, detail="Symbol not found")

    # Update fields
    if update.tag_number is not None:
        symbol.tag_number = update.tag_number
    if update.symbol_class is not None:
        symbol.symbol_class = update.symbol_class
    if update.is_verified is not None:
        symbol.is_verified = update.is_verified
    if update.is_flagged is not None:
        symbol.is_flagged = update.is_flagged

    db.commit()
    db.refresh(symbol)

    return SymbolResponse(
        id=str(symbol.id),
        symbol_class=symbol.symbol_class,
        category=symbol.category.value,
        tag_number=symbol.tag_number,
        bbox_x=symbol.bbox_x,
        bbox_y=symbol.bbox_y,
        bbox_width=symbol.bbox_width,
        bbox_height=symbol.bbox_height,
        confidence=symbol.confidence,
        is_verified=symbol.is_verified,
        is_flagged=symbol.is_flagged,
    )


@router.delete("/{drawing_id}/symbols/{symbol_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_symbol(
    drawing_id: UUID,
    symbol_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    hard_delete: bool = False,
) -> None:
    """Soft-delete a symbol (or hard delete if specified)."""
    drawing = await drawing_service.get_drawing(db, drawing_id)
    if not drawing:
        raise HTTPException(status_code=404, detail="Drawing not found")

    # Check project access
    project = db.query(Project).filter(Project.id == drawing.project_id).first()
    if not project or project.organization_id != current_user.organization_id:
        raise HTTPException(status_code=403, detail="Access denied")

    # Get symbol
    symbol = db.query(Symbol).filter(
        Symbol.id == symbol_id,
        Symbol.drawing_id == drawing_id,
    ).first()
    if not symbol:
        raise HTTPException(status_code=404, detail="Symbol not found")

    if hard_delete:
        db.delete(symbol)
    else:
        symbol.is_deleted = True
    db.commit()


@router.patch("/{drawing_id}/texts/{text_id}", response_model=TextAnnotationResponse)
async def update_text_annotation(
    drawing_id: UUID,
    text_id: UUID,
    update: TextUpdateRequest,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> TextAnnotationResponse:
    """Update a text annotation's content or verification status."""
    drawing = await drawing_service.get_drawing(db, drawing_id)
    if not drawing:
        raise HTTPException(status_code=404, detail="Drawing not found")

    # Check project access
    project = db.query(Project).filter(Project.id == drawing.project_id).first()
    if not project or project.organization_id != current_user.organization_id:
        raise HTTPException(status_code=403, detail="Access denied")

    # Get text annotation
    text = db.query(TextAnnotation).filter(
        TextAnnotation.id == text_id,
        TextAnnotation.drawing_id == drawing_id,
    ).first()
    if not text:
        raise HTTPException(status_code=404, detail="Text annotation not found")

    # Update fields
    if update.text_content is not None:
        text.text_content = update.text_content
    if update.is_verified is not None:
        text.is_verified = update.is_verified

    db.commit()
    db.refresh(text)

    return TextAnnotationResponse(
        id=str(text.id),
        text_content=text.text_content,
        bbox_x=text.bbox_x,
        bbox_y=text.bbox_y,
        bbox_width=text.bbox_width,
        bbox_height=text.bbox_height,
        rotation=text.rotation,
        confidence=text.confidence,
        is_verified=text.is_verified,
        associated_symbol_id=str(text.associated_symbol_id) if text.associated_symbol_id else None,
    )


@router.post("/{drawing_id}/symbols/{symbol_id}/verify", response_model=SymbolResponse)
async def verify_symbol(
    drawing_id: UUID,
    symbol_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> SymbolResponse:
    """Mark a symbol as verified."""
    drawing = await drawing_service.get_drawing(db, drawing_id)
    if not drawing:
        raise HTTPException(status_code=404, detail="Drawing not found")

    # Check project access
    project = db.query(Project).filter(Project.id == drawing.project_id).first()
    if not project or project.organization_id != current_user.organization_id:
        raise HTTPException(status_code=403, detail="Access denied")

    # Get symbol
    symbol = db.query(Symbol).filter(
        Symbol.id == symbol_id,
        Symbol.drawing_id == drawing_id,
    ).first()
    if not symbol:
        raise HTTPException(status_code=404, detail="Symbol not found")

    symbol.is_verified = True
    db.commit()
    db.refresh(symbol)

    return SymbolResponse(
        id=str(symbol.id),
        symbol_class=symbol.symbol_class,
        category=symbol.category.value,
        tag_number=symbol.tag_number,
        bbox_x=symbol.bbox_x,
        bbox_y=symbol.bbox_y,
        bbox_width=symbol.bbox_width,
        bbox_height=symbol.bbox_height,
        confidence=symbol.confidence,
        is_verified=symbol.is_verified,
        is_flagged=symbol.is_flagged,
    )


@router.post("/{drawing_id}/symbols/{symbol_id}/flag", response_model=SymbolResponse)
async def flag_symbol(
    drawing_id: UUID,
    symbol_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> SymbolResponse:
    """Mark a symbol as flagged for review."""
    drawing = await drawing_service.get_drawing(db, drawing_id)
    if not drawing:
        raise HTTPException(status_code=404, detail="Drawing not found")

    # Check project access
    project = db.query(Project).filter(Project.id == drawing.project_id).first()
    if not project or project.organization_id != current_user.organization_id:
        raise HTTPException(status_code=403, detail="Access denied")

    # Get symbol
    symbol = db.query(Symbol).filter(
        Symbol.id == symbol_id,
        Symbol.drawing_id == drawing_id,
    ).first()
    if not symbol:
        raise HTTPException(status_code=404, detail="Symbol not found")

    symbol.is_flagged = True
    db.commit()
    db.refresh(symbol)

    return SymbolResponse(
        id=str(symbol.id),
        symbol_class=symbol.symbol_class,
        category=symbol.category.value,
        tag_number=symbol.tag_number,
        bbox_x=symbol.bbox_x,
        bbox_y=symbol.bbox_y,
        bbox_width=symbol.bbox_width,
        bbox_height=symbol.bbox_height,
        confidence=symbol.confidence,
        is_verified=symbol.is_verified,
        is_flagged=symbol.is_flagged,
    )


@router.post("/{drawing_id}/symbols/{symbol_id}/unflag", response_model=SymbolResponse)
async def unflag_symbol(
    drawing_id: UUID,
    symbol_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> SymbolResponse:
    """Remove flag from a symbol."""
    drawing = await drawing_service.get_drawing(db, drawing_id)
    if not drawing:
        raise HTTPException(status_code=404, detail="Drawing not found")

    # Check project access
    project = db.query(Project).filter(Project.id == drawing.project_id).first()
    if not project or project.organization_id != current_user.organization_id:
        raise HTTPException(status_code=403, detail="Access denied")

    # Get symbol
    symbol = db.query(Symbol).filter(
        Symbol.id == symbol_id,
        Symbol.drawing_id == drawing_id,
    ).first()
    if not symbol:
        raise HTTPException(status_code=404, detail="Symbol not found")

    symbol.is_flagged = False
    db.commit()
    db.refresh(symbol)

    return SymbolResponse(
        id=str(symbol.id),
        symbol_class=symbol.symbol_class,
        category=symbol.category.value,
        tag_number=symbol.tag_number,
        bbox_x=symbol.bbox_x,
        bbox_y=symbol.bbox_y,
        bbox_width=symbol.bbox_width,
        bbox_height=symbol.bbox_height,
        confidence=symbol.confidence,
        is_verified=symbol.is_verified,
        is_flagged=symbol.is_flagged,
    )


class BulkVerifyRequest(BaseModel):
    symbol_ids: list[str]


class BulkVerifyResponse(BaseModel):
    verified_count: int
    verified_ids: list[str]
    failed_ids: list[str]


@router.post("/{drawing_id}/symbols/bulk-verify", response_model=BulkVerifyResponse)
async def bulk_verify_symbols(
    drawing_id: UUID,
    request: BulkVerifyRequest,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> BulkVerifyResponse:
    """Mark multiple symbols as verified in a single operation."""
    drawing = await drawing_service.get_drawing(db, drawing_id)
    if not drawing:
        raise HTTPException(status_code=404, detail="Drawing not found")

    # Check project access
    project = db.query(Project).filter(Project.id == drawing.project_id).first()
    if not project or project.organization_id != current_user.organization_id:
        raise HTTPException(status_code=403, detail="Access denied")

    verified_ids: list[str] = []
    failed_ids: list[str] = []

    for symbol_id_str in request.symbol_ids:
        try:
            symbol_id = UUID(symbol_id_str)
            symbol = db.query(Symbol).filter(
                Symbol.id == symbol_id,
                Symbol.drawing_id == drawing_id,
            ).first()
            if symbol and not symbol.is_verified:
                symbol.is_verified = True
                verified_ids.append(symbol_id_str)
            elif symbol and symbol.is_verified:
                # Already verified, still count as success
                verified_ids.append(symbol_id_str)
            else:
                failed_ids.append(symbol_id_str)
        except (ValueError, TypeError):
            # Invalid UUID format
            failed_ids.append(symbol_id_str)

    db.commit()

    return BulkVerifyResponse(
        verified_count=len(verified_ids),
        verified_ids=verified_ids,
        failed_ids=failed_ids,
    )


class BulkFlagRequest(BaseModel):
    symbol_ids: list[str]


class BulkFlagResponse(BaseModel):
    flagged_count: int
    flagged_ids: list[str]
    failed_ids: list[str]


@router.post("/{drawing_id}/symbols/bulk-flag", response_model=BulkFlagResponse)
async def bulk_flag_symbols(
    drawing_id: UUID,
    request: BulkFlagRequest,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> BulkFlagResponse:
    """Mark multiple symbols as flagged for review in a single operation."""
    drawing = await drawing_service.get_drawing(db, drawing_id)
    if not drawing:
        raise HTTPException(status_code=404, detail="Drawing not found")

    # Check project access
    project = db.query(Project).filter(Project.id == drawing.project_id).first()
    if not project or project.organization_id != current_user.organization_id:
        raise HTTPException(status_code=403, detail="Access denied")

    flagged_ids: list[str] = []
    failed_ids: list[str] = []

    for symbol_id_str in request.symbol_ids:
        try:
            symbol_id = UUID(symbol_id_str)
            symbol = db.query(Symbol).filter(
                Symbol.id == symbol_id,
                Symbol.drawing_id == drawing_id,
            ).first()
            if symbol and not symbol.is_flagged:
                symbol.is_flagged = True
                flagged_ids.append(symbol_id_str)
            elif symbol and symbol.is_flagged:
                # Already flagged, still count as success
                flagged_ids.append(symbol_id_str)
            else:
                failed_ids.append(symbol_id_str)
        except (ValueError, TypeError):
            # Invalid UUID format
            failed_ids.append(symbol_id_str)

    db.commit()

    return BulkFlagResponse(
        flagged_count=len(flagged_ids),
        flagged_ids=flagged_ids,
        failed_ids=failed_ids,
    )


@router.post("/{drawing_id}/symbols/bulk-unflag", response_model=BulkFlagResponse)
async def bulk_unflag_symbols(
    drawing_id: UUID,
    request: BulkFlagRequest,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> BulkFlagResponse:
    """Remove flag from multiple symbols in a single operation."""
    drawing = await drawing_service.get_drawing(db, drawing_id)
    if not drawing:
        raise HTTPException(status_code=404, detail="Drawing not found")

    # Check project access
    project = db.query(Project).filter(Project.id == drawing.project_id).first()
    if not project or project.organization_id != current_user.organization_id:
        raise HTTPException(status_code=403, detail="Access denied")

    unflagged_ids: list[str] = []
    failed_ids: list[str] = []

    for symbol_id_str in request.symbol_ids:
        try:
            symbol_id = UUID(symbol_id_str)
            symbol = db.query(Symbol).filter(
                Symbol.id == symbol_id,
                Symbol.drawing_id == drawing_id,
            ).first()
            if symbol and symbol.is_flagged:
                symbol.is_flagged = False
                unflagged_ids.append(symbol_id_str)
            elif symbol and not symbol.is_flagged:
                # Already unflagged, still count as success
                unflagged_ids.append(symbol_id_str)
            else:
                failed_ids.append(symbol_id_str)
        except (ValueError, TypeError):
            # Invalid UUID format
            failed_ids.append(symbol_id_str)

    db.commit()

    return BulkFlagResponse(
        flagged_count=len(unflagged_ids),
        flagged_ids=unflagged_ids,
        failed_ids=failed_ids,
    )


# Title block extraction models and endpoint
class TitleBlockResponse(BaseModel):
    """Title block information extracted from the drawing."""

    drawing_number: str | None = None
    revision: str | None = None
    title: str | None = None
    project_name: str | None = None
    date: str | None = None
    scale: str | None = None
    drawn_by: str | None = None
    checked_by: str | None = None
    approved_by: str | None = None
    sheet: str | None = None
    # Source info for debugging/verification
    extraction_confidence: float = 0.0
    texts_analyzed: int = 0


def _extract_title_block_from_texts(
    texts: list[TextAnnotation],
    image_width: float = 841.0,  # A1 landscape width in mm
    image_height: float = 594.0,  # A1 landscape height in mm
) -> TitleBlockResponse:
    """
    Extract title block information from text annotations.

    Title blocks are typically in the bottom-right corner of the drawing.
    Uses position-based filtering and pattern matching to identify fields.
    """
    import re

    # Filter texts in the title block region (bottom-right quadrant)
    # Title blocks are typically in the bottom 20% and right 40% of the drawing
    title_block_texts = []
    for text in texts:
        if text.is_deleted:
            continue
        # Check if text is in title block region
        x_ratio = text.bbox_x / image_width if image_width > 0 else 0
        y_ratio = text.bbox_y / image_height if image_height > 0 else 0

        # Title block region: right 40%, bottom 25%
        if x_ratio >= 0.60 and y_ratio >= 0.75:
            title_block_texts.append(text)

    if not title_block_texts:
        # Fallback: look at all texts and try pattern matching
        title_block_texts = [t for t in texts if not t.is_deleted]

    # Initialize result
    result = TitleBlockResponse(texts_analyzed=len(title_block_texts))

    if not title_block_texts:
        return result

    # Patterns for common title block fields
    patterns = {
        # Drawing number patterns (e.g., P&ID-001, DWG-12345, 100-PID-001)
        "drawing_number": [
            r"(?:P&ID|PID|DWG|DRAWING)[-\s]?(\d{3,6}[A-Z]?)",
            r"(\d{2,3}[-/]\w{3,4}[-/]\d{3,6})",
            r"^([A-Z]{2,4}[-/]\d{3,6}[A-Z]?)$",
        ],
        # Revision patterns (e.g., REV A, R1, REVISION 2)
        # Note: Must use word boundary to avoid matching partial words like DRAWN
        "revision": [
            r"\bREV(?:ISION)?[\s.:]*([A-Z0-9]{1,3})\b",
            r"^REV\s+([A-Z0-9]{1,3})$",
            r"^([A-Z])$",  # Single letter revision (entire text is just one letter)
        ],
        # Scale patterns (e.g., 1:50, SCALE: 1/100)
        "scale": [
            r"(?:SCALE)?[\s.:]*(\d+\s*[:/]\s*\d+)",
            r"^(\d+:\d+)$",
        ],
        # Date patterns (various formats) - order matters: 4-digit year first
        "date": [
            r"(\d{4}[-/]\d{1,2}[-/]\d{1,2})",  # ISO format: 2025-12-15
            r"(\d{1,2}[-/]\d{1,2}[-/]\d{4})",  # DD/MM/YYYY or MM/DD/YYYY
            r"(\d{1,2}[-/]\d{1,2}[-/]\d{2})",  # Short year: 15/12/25
            r"(?:DATE)?[\s.:]*(\d{1,2}\s+\w{3,9}\s+\d{4})",  # 15 January 2025
        ],
        # Sheet patterns (e.g., SHEET 1 OF 5, 1/5)
        "sheet": [
            r"(?:SHEET|SH)[\s.:]*(\d+\s*(?:OF|/)\s*\d+)",
            r"^(\d+\s*/\s*\d+)$",
        ],
    }

    # Personnel patterns with field prefixes
    personnel_patterns = {
        "drawn_by": [
            r"(?:DRAWN|DRAFTED|DRN|BY)[\s.:]*([A-Z]{2,4})",
            r"(?:DRAWN|DRAFTED|DRN|BY)[\s.:]*([A-Za-z\s]{2,20})",
        ],
        "checked_by": [
            r"(?:CHECKED|CHK|CK)[\s.:]*([A-Z]{2,4})",
            r"(?:CHECKED|CHK|CK)[\s.:]*([A-Za-z\s]{2,20})",
        ],
        "approved_by": [
            r"(?:APPROVED|APPR|APP|APR)[\s.:]*([A-Z]{2,4})",
            r"(?:APPROVED|APPR|APP|APR)[\s.:]*([A-Za-z\s]{2,20})",
        ],
    }

    # Sort texts by position (bottom to top, right to left) for better matching
    sorted_texts = sorted(
        title_block_texts,
        key=lambda t: (-t.bbox_y, -t.bbox_x),
    )

    matched_fields = 0
    total_patterns = len(patterns) + len(personnel_patterns)

    # Extract using patterns
    for text in sorted_texts:
        content = text.text_content.strip().upper()

        # Try each pattern category
        for field, pattern_list in patterns.items():
            if getattr(result, field) is not None:
                continue  # Already found
            for pattern in pattern_list:
                match = re.search(pattern, content, re.IGNORECASE)
                if match:
                    setattr(result, field, match.group(1).strip())
                    matched_fields += 1
                    break

        for field, pattern_list in personnel_patterns.items():
            if getattr(result, field) is not None:
                continue
            for pattern in pattern_list:
                match = re.search(pattern, content, re.IGNORECASE)
                if match:
                    setattr(result, field, match.group(1).strip())
                    matched_fields += 1
                    break

    # Look for title (usually the longest text in the title block area)
    if result.title is None:
        potential_titles = [
            t.text_content
            for t in title_block_texts
            if len(t.text_content) > 10
            and not any(
                kw in t.text_content.upper()
                for kw in ["SCALE", "REV", "DATE", "SHEET", "DRAWN", "CHECKED", "APPR"]
            )
        ]
        if potential_titles:
            # Take the longest one as the title
            result.title = max(potential_titles, key=len)
            matched_fields += 1

    # Look for project name (often contains "PROJECT" or similar)
    if result.project_name is None:
        for text in title_block_texts:
            content = text.text_content.upper()
            if "PROJECT" in content or "PLANT" in content or "FACILITY" in content:
                # Extract the value after the keyword
                for kw in ["PROJECT:", "PROJECT", "PLANT:", "PLANT"]:
                    if kw in content:
                        idx = content.find(kw) + len(kw)
                        result.project_name = text.text_content[idx:].strip()
                        matched_fields += 1
                        break
                if result.project_name:
                    break

    # Calculate extraction confidence
    result.extraction_confidence = matched_fields / total_patterns if total_patterns > 0 else 0.0

    return result


@router.get("/{drawing_id}/title-block", response_model=TitleBlockResponse)
async def get_title_block(
    drawing_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> TitleBlockResponse:
    """
    Extract title block information from a drawing.

    Analyzes text annotations in the title block region (typically bottom-right)
    and uses pattern matching to extract structured fields like drawing number,
    revision, title, project name, date, scale, and personnel signatures.

    Returns extracted fields with an extraction confidence score.
    """
    drawing = await drawing_service.get_drawing(db, drawing_id)
    if not drawing:
        raise HTTPException(status_code=404, detail="Drawing not found")

    # Check project access
    project = db.query(Project).filter(Project.id == drawing.project_id).first()
    if not project or project.organization_id != current_user.organization_id:
        raise HTTPException(status_code=403, detail="Access denied")

    # Check if drawing has been processed
    if drawing.status not in [DrawingStatus.review, DrawingStatus.complete]:
        raise HTTPException(
            status_code=400,
            detail="Drawing must be processed before title block can be extracted",
        )

    # Get all text annotations for this drawing
    texts = (
        db.query(TextAnnotation)
        .filter(
            TextAnnotation.drawing_id == drawing_id,
            TextAnnotation.is_deleted == False,  # noqa: E712
        )
        .all()
    )

    # Extract title block information
    return _extract_title_block_from_texts(texts)


# =============================================================================
# Line/Connection CRUD Endpoints (EDIT-05)
# =============================================================================


class LineResponse(BaseModel):
    """Response model for a line/connection."""

    id: str
    line_number: str | None
    start_x: float
    start_y: float
    end_x: float
    end_y: float
    line_spec: str | None
    pipe_class: str | None
    insulation: str | None
    confidence: float | None
    is_verified: bool
    is_deleted: bool

    model_config = ConfigDict(from_attributes=True)


class LinesResponse(BaseModel):
    """Response model for list of lines with summary."""

    lines: list[LineResponse]
    summary: dict[str, int]


class LineCreateRequest(BaseModel):
    """Request model for creating a new line."""

    line_number: str | None = None
    start_x: float
    start_y: float
    end_x: float
    end_y: float
    line_spec: str | None = None
    pipe_class: str | None = None
    insulation: str | None = None
    confidence: float | None = None
    is_verified: bool = False


class LineUpdateRequest(BaseModel):
    """Request model for updating a line."""

    line_number: str | None = None
    start_x: float | None = None
    start_y: float | None = None
    end_x: float | None = None
    end_y: float | None = None
    line_spec: str | None = None
    pipe_class: str | None = None
    insulation: str | None = None
    is_verified: bool | None = None


class BulkLineVerifyRequest(BaseModel):
    """Request model for bulk line verification."""

    line_ids: list[str]


class BulkLineVerifyResponse(BaseModel):
    """Response model for bulk line verification."""

    verified_count: int
    verified_ids: list[str]
    failed_ids: list[str]


@router.get("/{drawing_id}/lines", response_model=LinesResponse)
async def get_drawing_lines(
    drawing_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    include_deleted: bool = False,
) -> LinesResponse:
    """
    Get all detected lines/connections for a drawing.

    Lines represent piping connections between symbols on the P&ID.
    """
    drawing = await drawing_service.get_drawing(db, drawing_id)
    if not drawing:
        raise HTTPException(status_code=404, detail="Drawing not found")

    # Check project access
    project = db.query(Project).filter(Project.id == drawing.project_id).first()
    if not project or project.organization_id != current_user.organization_id:
        raise HTTPException(status_code=403, detail="Access denied")

    # Get lines
    lines_query = db.query(Line).filter(Line.drawing_id == drawing_id)
    if not include_deleted:
        lines_query = lines_query.filter(Line.is_deleted == False)  # noqa: E712
    lines = lines_query.order_by(Line.created_at).all()

    # Build response
    line_responses = [
        LineResponse(
            id=str(line.id),
            line_number=line.line_number,
            start_x=line.start_x,
            start_y=line.start_y,
            end_x=line.end_x,
            end_y=line.end_y,
            line_spec=line.line_spec,
            pipe_class=line.pipe_class,
            insulation=line.insulation,
            confidence=line.confidence,
            is_verified=line.is_verified,
            is_deleted=line.is_deleted,
        )
        for line in lines
    ]

    # Summary stats
    verified_lines = sum(1 for line in lines if line.is_verified)
    low_confidence_lines = sum(
        1 for line in lines if line.confidence and line.confidence < 0.85
    )

    return LinesResponse(
        lines=line_responses,
        summary={
            "total_lines": len(lines),
            "verified_lines": verified_lines,
            "pending_lines": len(lines) - verified_lines,
            "low_confidence_lines": low_confidence_lines,
        },
    )


@router.post("/{drawing_id}/lines", response_model=LineResponse, status_code=201)
async def create_line(
    drawing_id: UUID,
    line_data: LineCreateRequest,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> LineResponse:
    """
    Create a new line/connection (manually add a missing line).

    Used when a piping connection was not detected by AI and needs to be added manually.
    """
    drawing = await drawing_service.get_drawing(db, drawing_id)
    if not drawing:
        raise HTTPException(status_code=404, detail="Drawing not found")

    # Check project access
    project = db.query(Project).filter(Project.id == drawing.project_id).first()
    if not project or project.organization_id != current_user.organization_id:
        raise HTTPException(status_code=403, detail="Access denied")

    # Create new line
    line = Line(
        drawing_id=drawing_id,
        line_number=line_data.line_number,
        start_x=line_data.start_x,
        start_y=line_data.start_y,
        end_x=line_data.end_x,
        end_y=line_data.end_y,
        line_spec=line_data.line_spec,
        pipe_class=line_data.pipe_class,
        insulation=line_data.insulation,
        confidence=line_data.confidence,
        is_verified=line_data.is_verified,
    )

    db.add(line)
    db.commit()
    db.refresh(line)

    return LineResponse(
        id=str(line.id),
        line_number=line.line_number,
        start_x=line.start_x,
        start_y=line.start_y,
        end_x=line.end_x,
        end_y=line.end_y,
        line_spec=line.line_spec,
        pipe_class=line.pipe_class,
        insulation=line.insulation,
        confidence=line.confidence,
        is_verified=line.is_verified,
        is_deleted=line.is_deleted,
    )


@router.patch("/{drawing_id}/lines/{line_id}", response_model=LineResponse)
async def update_line(
    drawing_id: UUID,
    line_id: UUID,
    update: LineUpdateRequest,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> LineResponse:
    """
    Update a line's properties.

    Can update line number, coordinates, spec, pipe class, insulation, or verification status.
    """
    drawing = await drawing_service.get_drawing(db, drawing_id)
    if not drawing:
        raise HTTPException(status_code=404, detail="Drawing not found")

    # Check project access
    project = db.query(Project).filter(Project.id == drawing.project_id).first()
    if not project or project.organization_id != current_user.organization_id:
        raise HTTPException(status_code=403, detail="Access denied")

    # Get line
    line = db.query(Line).filter(
        Line.id == line_id,
        Line.drawing_id == drawing_id,
    ).first()
    if not line:
        raise HTTPException(status_code=404, detail="Line not found")

    # Update fields
    if update.line_number is not None:
        line.line_number = update.line_number
    if update.start_x is not None:
        line.start_x = update.start_x
    if update.start_y is not None:
        line.start_y = update.start_y
    if update.end_x is not None:
        line.end_x = update.end_x
    if update.end_y is not None:
        line.end_y = update.end_y
    if update.line_spec is not None:
        line.line_spec = update.line_spec
    if update.pipe_class is not None:
        line.pipe_class = update.pipe_class
    if update.insulation is not None:
        line.insulation = update.insulation
    if update.is_verified is not None:
        line.is_verified = update.is_verified

    db.commit()
    db.refresh(line)

    return LineResponse(
        id=str(line.id),
        line_number=line.line_number,
        start_x=line.start_x,
        start_y=line.start_y,
        end_x=line.end_x,
        end_y=line.end_y,
        line_spec=line.line_spec,
        pipe_class=line.pipe_class,
        insulation=line.insulation,
        confidence=line.confidence,
        is_verified=line.is_verified,
        is_deleted=line.is_deleted,
    )


@router.delete("/{drawing_id}/lines/{line_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_line(
    drawing_id: UUID,
    line_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    hard_delete: bool = False,
) -> None:
    """
    Soft-delete a line (or hard delete if specified).

    Soft delete marks the line as deleted but keeps it for undo/redo.
    Hard delete permanently removes the line from the database.
    """
    drawing = await drawing_service.get_drawing(db, drawing_id)
    if not drawing:
        raise HTTPException(status_code=404, detail="Drawing not found")

    # Check project access
    project = db.query(Project).filter(Project.id == drawing.project_id).first()
    if not project or project.organization_id != current_user.organization_id:
        raise HTTPException(status_code=403, detail="Access denied")

    # Get line
    line = db.query(Line).filter(
        Line.id == line_id,
        Line.drawing_id == drawing_id,
    ).first()
    if not line:
        raise HTTPException(status_code=404, detail="Line not found")

    if hard_delete:
        db.delete(line)
    else:
        line.is_deleted = True
    db.commit()


@router.post("/{drawing_id}/lines/{line_id}/verify", response_model=LineResponse)
async def verify_line(
    drawing_id: UUID,
    line_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> LineResponse:
    """Mark a line as verified."""
    drawing = await drawing_service.get_drawing(db, drawing_id)
    if not drawing:
        raise HTTPException(status_code=404, detail="Drawing not found")

    # Check project access
    project = db.query(Project).filter(Project.id == drawing.project_id).first()
    if not project or project.organization_id != current_user.organization_id:
        raise HTTPException(status_code=403, detail="Access denied")

    # Get line
    line = db.query(Line).filter(
        Line.id == line_id,
        Line.drawing_id == drawing_id,
    ).first()
    if not line:
        raise HTTPException(status_code=404, detail="Line not found")

    line.is_verified = True
    db.commit()
    db.refresh(line)

    return LineResponse(
        id=str(line.id),
        line_number=line.line_number,
        start_x=line.start_x,
        start_y=line.start_y,
        end_x=line.end_x,
        end_y=line.end_y,
        line_spec=line.line_spec,
        pipe_class=line.pipe_class,
        insulation=line.insulation,
        confidence=line.confidence,
        is_verified=line.is_verified,
        is_deleted=line.is_deleted,
    )


@router.post("/{drawing_id}/lines/{line_id}/unverify", response_model=LineResponse)
async def unverify_line(
    drawing_id: UUID,
    line_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> LineResponse:
    """Remove verification from a line."""
    drawing = await drawing_service.get_drawing(db, drawing_id)
    if not drawing:
        raise HTTPException(status_code=404, detail="Drawing not found")

    # Check project access
    project = db.query(Project).filter(Project.id == drawing.project_id).first()
    if not project or project.organization_id != current_user.organization_id:
        raise HTTPException(status_code=403, detail="Access denied")

    # Get line
    line = db.query(Line).filter(
        Line.id == line_id,
        Line.drawing_id == drawing_id,
    ).first()
    if not line:
        raise HTTPException(status_code=404, detail="Line not found")

    line.is_verified = False
    db.commit()
    db.refresh(line)

    return LineResponse(
        id=str(line.id),
        line_number=line.line_number,
        start_x=line.start_x,
        start_y=line.start_y,
        end_x=line.end_x,
        end_y=line.end_y,
        line_spec=line.line_spec,
        pipe_class=line.pipe_class,
        insulation=line.insulation,
        confidence=line.confidence,
        is_verified=line.is_verified,
        is_deleted=line.is_deleted,
    )


@router.post("/{drawing_id}/lines/bulk-verify", response_model=BulkLineVerifyResponse)
async def bulk_verify_lines(
    drawing_id: UUID,
    request: BulkLineVerifyRequest,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> BulkLineVerifyResponse:
    """Mark multiple lines as verified in a single operation."""
    drawing = await drawing_service.get_drawing(db, drawing_id)
    if not drawing:
        raise HTTPException(status_code=404, detail="Drawing not found")

    # Check project access
    project = db.query(Project).filter(Project.id == drawing.project_id).first()
    if not project or project.organization_id != current_user.organization_id:
        raise HTTPException(status_code=403, detail="Access denied")

    verified_ids: list[str] = []
    failed_ids: list[str] = []

    for line_id_str in request.line_ids:
        try:
            line_id = UUID(line_id_str)
            line = db.query(Line).filter(
                Line.id == line_id,
                Line.drawing_id == drawing_id,
            ).first()
            if line and not line.is_verified:
                line.is_verified = True
                verified_ids.append(line_id_str)
            elif line and line.is_verified:
                # Already verified, still count as success
                verified_ids.append(line_id_str)
            else:
                failed_ids.append(line_id_str)
        except (ValueError, TypeError):
            # Invalid UUID format
            failed_ids.append(line_id_str)

    db.commit()

    return BulkLineVerifyResponse(
        verified_count=len(verified_ids),
        verified_ids=verified_ids,
        failed_ids=failed_ids,
    )


@router.post("/{drawing_id}/lines/{line_id}/restore", response_model=LineResponse)
async def restore_line(
    drawing_id: UUID,
    line_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> LineResponse:
    """
    Restore a soft-deleted line.

    Used for undo functionality after deleting a line.
    """
    drawing = await drawing_service.get_drawing(db, drawing_id)
    if not drawing:
        raise HTTPException(status_code=404, detail="Drawing not found")

    # Check project access
    project = db.query(Project).filter(Project.id == drawing.project_id).first()
    if not project or project.organization_id != current_user.organization_id:
        raise HTTPException(status_code=403, detail="Access denied")

    # Get line (including deleted)
    line = db.query(Line).filter(
        Line.id == line_id,
        Line.drawing_id == drawing_id,
    ).first()
    if not line:
        raise HTTPException(status_code=404, detail="Line not found")

    if not line.is_deleted:
        raise HTTPException(status_code=400, detail="Line is not deleted")

    line.is_deleted = False
    db.commit()
    db.refresh(line)

    return LineResponse(
        id=str(line.id),
        line_number=line.line_number,
        start_x=line.start_x,
        start_y=line.start_y,
        end_x=line.end_x,
        end_y=line.end_y,
        line_spec=line.line_spec,
        pipe_class=line.pipe_class,
        insulation=line.insulation,
        confidence=line.confidence,
        is_verified=line.is_verified,
        is_deleted=line.is_deleted,
    )

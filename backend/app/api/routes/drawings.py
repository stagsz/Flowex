from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile, status
from fastapi.responses import Response
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session

from app.core.config import StorageProvider, settings
from app.core.deps import get_current_user, get_db
from app.models import DrawingStatus, Project, Symbol, TextAnnotation, User
from app.services import drawings as drawing_service
from app.services.drawings import FileValidationError
from app.services.storage import get_storage_service

router = APIRouter(prefix="/drawings", tags=["drawings"])


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
    )


@router.get("/project/{project_id}", response_model=list[DrawingResponse])
async def list_drawings(
    project_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    skip: int = 0,
    limit: int = 100,
) -> list[DrawingResponse]:
    """List all drawings for a project."""
    # Check project access
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    if project.organization_id != current_user.organization_id:
        raise HTTPException(status_code=403, detail="Access denied")

    drawings = await drawing_service.get_drawings_by_project(db, project_id, skip, limit)

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
    """Get a drawing by ID with download URL."""
    drawing = await drawing_service.get_drawing(db, drawing_id)
    if not drawing:
        raise HTTPException(status_code=404, detail="Drawing not found")

    # Check project access
    project = db.query(Project).filter(Project.id == drawing.project_id).first()
    if not project or project.organization_id != current_user.organization_id:
        raise HTTPException(status_code=403, detail="Access denied")

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

    task = process_drawing.delay(str(drawing_id))

    return ProcessingResponse(
        drawing_id=str(drawing_id),
        task_id=task.id,
        status="queued",
        message="Processing task has been queued",
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


class SymbolUpdateRequest(BaseModel):
    tag_number: str | None = None
    symbol_class: str | None = None
    is_verified: bool | None = None


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
    low_confidence_symbols = sum(1 for s in symbols if s.confidence and s.confidence < 0.85)

    return SymbolsAndTextsResponse(
        symbols=symbol_responses,
        texts=text_responses,
        summary={
            "total_symbols": len(symbols),
            "verified_symbols": verified_symbols,
            "low_confidence_symbols": low_confidence_symbols,
            "total_texts": len(texts),
            "verified_texts": sum(1 for t in texts if t.is_verified),
        },
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
    )

"""Export API routes for DXF and data list generation."""

import logging
from pathlib import Path
from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.deps import get_current_user, get_db
from app.models import Drawing, Line, Project, Symbol, TextAnnotation, User
from app.services.export.data_lists import (
    DataListExportService,
    ExportFormat,
    ExportMetadata,
)
from app.services.export.dxf_export import (
    DXFExportService,
    ExportOptions,
    PaperSize,
    TitleBlockInfo,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/exports", tags=["exports"])


# Request/Response models


class DXFExportRequest(BaseModel):
    """Request body for DXF export."""

    format: str = "dxf"  # dxf or dwg
    paper_size: str = "A1"  # A0, A1, A2, A3, A4
    scale: str = "1:50"
    include_connections: bool = True
    include_annotations: bool = True
    include_title_block: bool = True


class DataListExportRequest(BaseModel):
    """Request body for data list export."""

    lists: list[str] = ["equipment", "line", "instrument", "valve", "mto"]
    format: str = "xlsx"  # xlsx, csv, pdf
    include_unverified: bool = False


class ChecklistExportRequest(BaseModel):
    """Request body for validation checklist export."""

    format: str = "pdf"  # pdf, xlsx, csv
    include_unverified: bool = True


class ExportJobResponse(BaseModel):
    """Response for export job creation."""

    job_id: str
    drawing_id: str
    export_type: str
    status: str
    message: str


class ExportStatusResponse(BaseModel):
    """Response for export job status."""

    job_id: str
    status: str
    file_path: str | None = None
    error: str | None = None


# In-memory job tracking (in production, use Redis or database)
_export_jobs: dict[str, dict[str, Any]] = {}


def _get_drawing_with_access_check(
    drawing_id: UUID,
    db: Session,
    current_user: User,
) -> Drawing:
    """Get drawing and verify user has access."""
    drawing = db.query(Drawing).filter(Drawing.id == drawing_id).first()
    if not drawing:
        raise HTTPException(status_code=404, detail="Drawing not found")

    project = db.query(Project).filter(Project.id == drawing.project_id).first()
    if not project or project.organization_id != current_user.organization_id:
        raise HTTPException(status_code=403, detail="Access denied")

    return drawing


def _get_drawing_data(
    db: Session,
    drawing_id: UUID,
) -> tuple[list[Symbol], list[Line], list[TextAnnotation]]:
    """Get all related data for a drawing."""
    symbols = db.query(Symbol).filter(Symbol.drawing_id == drawing_id).all()
    lines = db.query(Line).filter(Line.drawing_id == drawing_id).all()
    text_annotations = (
        db.query(TextAnnotation).filter(TextAnnotation.drawing_id == drawing_id).all()
    )
    return symbols, lines, text_annotations


def _create_export_metadata(drawing: Drawing, db: Session) -> ExportMetadata:
    """Create export metadata from drawing."""
    project = db.query(Project).filter(Project.id == drawing.project_id).first()
    return ExportMetadata(
        project_name=project.name if project else "Unknown",
        drawing_number=drawing.original_filename.rsplit(".", 1)[0],
    )


# DXF Export Endpoints


@router.post(
    "/drawings/{drawing_id}/dxf",
    response_model=ExportJobResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def export_drawing_dxf(
    drawing_id: UUID,
    request: DXFExportRequest,
    background_tasks: BackgroundTasks,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> ExportJobResponse:
    """
    Start DXF export for a drawing.

    Returns a job ID that can be used to check status and download the file.
    """
    _get_drawing_with_access_check(drawing_id, db, current_user)

    # Validate paper size
    try:
        paper_size = PaperSize(request.paper_size)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid paper size. Must be one of: {[p.value for p in PaperSize]}",
        )

    # Create job
    import uuid

    job_id = str(uuid.uuid4())
    _export_jobs[job_id] = {
        "status": "processing",
        "drawing_id": str(drawing_id),
        "export_type": "dxf",
        "file_path": None,
        "error": None,
    }

    # Queue background task
    background_tasks.add_task(
        _process_dxf_export,
        job_id,
        drawing_id,
        request,
        paper_size,
    )

    return ExportJobResponse(
        job_id=job_id,
        drawing_id=str(drawing_id),
        export_type="dxf",
        status="processing",
        message="DXF export job has been queued",
    )


async def _process_dxf_export(
    job_id: str,
    drawing_id: UUID,
    request: DXFExportRequest,
    paper_size: PaperSize,
) -> None:
    """Background task to process DXF export."""
    from app.core.database import SessionLocal

    logger.info(f"Starting DXF export for job {job_id}, drawing {drawing_id}")

    db = SessionLocal()
    try:
        drawing = db.query(Drawing).filter(Drawing.id == drawing_id).first()
        if not drawing:
            logger.error(f"Drawing {drawing_id} not found for job {job_id}")
            _export_jobs[job_id]["status"] = "failed"
            _export_jobs[job_id]["error"] = "Drawing not found"
            return

        logger.info(f"Found drawing: {drawing.original_filename}")
        symbols, lines, text_annotations = _get_drawing_data(db, drawing_id)
        logger.info(f"Data: {len(symbols)} symbols, {len(lines)} lines, {len(text_annotations)} texts")

        # Create export options
        options = ExportOptions(
            format=request.format,
            paper_size=paper_size,
            scale=request.scale,
            include_connections=request.include_connections,
            include_annotations=request.include_annotations,
            include_title_block=request.include_title_block,
        )

        # Create title block info
        project = db.query(Project).filter(Project.id == drawing.project_id).first()
        title_info = TitleBlockInfo(
            drawing_number=drawing.original_filename.rsplit(".", 1)[0],
            drawing_title=drawing.original_filename,
            project_name=project.name if project else "Unknown",
        )

        # Export
        logger.info(f"Creating DXF export service for job {job_id}")
        service = DXFExportService()
        output_path = service.export_drawing(
            drawing, symbols, lines, text_annotations, options, title_info
        )

        logger.info(f"DXF export completed for job {job_id}: {output_path}")
        _export_jobs[job_id]["status"] = "completed"
        _export_jobs[job_id]["file_path"] = str(output_path)

    except Exception as e:
        logger.exception(f"DXF export failed for job {job_id}: {e}")
        _export_jobs[job_id]["status"] = "failed"
        _export_jobs[job_id]["error"] = str(e)
    finally:
        db.close()


# Data List Export Endpoints


@router.post(
    "/drawings/{drawing_id}/lists",
    response_model=ExportJobResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def export_data_lists(
    drawing_id: UUID,
    request: DataListExportRequest,
    background_tasks: BackgroundTasks,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> ExportJobResponse:
    """
    Start data list export for a drawing.

    Available lists: equipment, line, instrument, valve, mto
    Available formats: xlsx, csv, pdf
    """
    _get_drawing_with_access_check(drawing_id, db, current_user)

    # Validate format
    try:
        export_format = ExportFormat(request.format)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid format. Must be one of: {[f.value for f in ExportFormat]}",
        )

    # Validate list types
    valid_lists = {"equipment", "line", "instrument", "valve", "mto", "report"}
    invalid_lists = set(request.lists) - valid_lists
    if invalid_lists:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid list types: {invalid_lists}. Must be one of: {valid_lists}",
        )

    # Create job
    import uuid

    job_id = str(uuid.uuid4())
    _export_jobs[job_id] = {
        "status": "processing",
        "drawing_id": str(drawing_id),
        "export_type": "data_lists",
        "file_paths": {},
        "error": None,
    }

    # Queue background task
    background_tasks.add_task(
        _process_data_list_export,
        job_id,
        drawing_id,
        request.lists,
        export_format,
        request.include_unverified,
    )

    return ExportJobResponse(
        job_id=job_id,
        drawing_id=str(drawing_id),
        export_type="data_lists",
        status="processing",
        message="Data list export job has been queued",
    )


async def _process_data_list_export(
    job_id: str,
    drawing_id: UUID,
    list_types: list[str],
    export_format: ExportFormat,
    include_unverified: bool,
) -> None:
    """Background task to process data list export."""
    from app.core.database import SessionLocal

    db = SessionLocal()
    try:
        drawing = db.query(Drawing).filter(Drawing.id == drawing_id).first()
        if not drawing:
            _export_jobs[job_id]["status"] = "failed"
            _export_jobs[job_id]["error"] = "Drawing not found"
            return

        symbols, lines, text_annotations = _get_drawing_data(db, drawing_id)
        metadata = _create_export_metadata(drawing, db)

        service = DataListExportService()
        file_paths: dict[str, str] = {}
        successful_paths: dict[str, Path] = {}

        for list_type in list_types:
            try:
                if list_type == "equipment":
                    path = service.export_equipment_list(
                        drawing, symbols, metadata, export_format, include_unverified
                    )
                elif list_type == "line":
                    path = service.export_line_list(
                        drawing, lines, metadata, export_format, include_unverified
                    )
                elif list_type == "instrument":
                    path = service.export_instrument_list(
                        drawing, symbols, metadata, export_format, include_unverified
                    )
                elif list_type == "valve":
                    path = service.export_valve_list(
                        drawing, symbols, metadata, export_format, include_unverified
                    )
                elif list_type == "mto":
                    path = service.export_mto(
                        drawing, symbols, lines, metadata, export_format, include_unverified
                    )
                elif list_type == "report":
                    path = service.export_comparison_report(
                        drawing, symbols, lines, text_annotations, metadata, export_format
                    )
                else:
                    continue

                file_paths[list_type] = str(path)
                successful_paths[list_type] = path
            except Exception as e:
                logger.exception(f"Failed to export {list_type}")
                file_paths[list_type] = f"error: {str(e)}"

        # If multiple files were created successfully, create a zip
        if len(successful_paths) > 1:
            drawing_name = drawing.original_filename.rsplit(".", 1)[0]
            zip_filename = f"{drawing_name}_data_lists.zip"
            zip_path = service.create_zip_from_files(successful_paths, zip_filename)
            _export_jobs[job_id]["file_path"] = str(zip_path)
        elif len(successful_paths) == 1:
            # Single file - use it directly
            _export_jobs[job_id]["file_path"] = str(next(iter(successful_paths.values())))

        _export_jobs[job_id]["status"] = "completed"
        _export_jobs[job_id]["file_paths"] = file_paths

    except Exception as e:
        logger.exception(f"Data list export failed for job {job_id}")
        _export_jobs[job_id]["status"] = "failed"
        _export_jobs[job_id]["error"] = str(e)
    finally:
        db.close()


# Comparison Report Endpoint


@router.post(
    "/drawings/{drawing_id}/report",
    response_model=ExportJobResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def export_comparison_report(
    drawing_id: UUID,
    background_tasks: BackgroundTasks,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    format: str = Query(default="pdf", description="Export format: pdf, xlsx, csv"),
) -> ExportJobResponse:
    """
    Generate extraction summary/comparison report.
    """
    _get_drawing_with_access_check(drawing_id, db, current_user)

    try:
        export_format = ExportFormat(format)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid format. Must be one of: {[f.value for f in ExportFormat]}",
        )

    import uuid

    job_id = str(uuid.uuid4())
    _export_jobs[job_id] = {
        "status": "processing",
        "drawing_id": str(drawing_id),
        "export_type": "report",
        "file_path": None,
        "error": None,
    }

    background_tasks.add_task(
        _process_report_export,
        job_id,
        drawing_id,
        export_format,
    )

    return ExportJobResponse(
        job_id=job_id,
        drawing_id=str(drawing_id),
        export_type="report",
        status="processing",
        message="Comparison report export job has been queued",
    )


# Validation Checklist Export Endpoint


@router.post(
    "/drawings/{drawing_id}/checklist",
    response_model=ExportJobResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def export_validation_checklist(
    drawing_id: UUID,
    request: ChecklistExportRequest,
    background_tasks: BackgroundTasks,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> ExportJobResponse:
    """
    Export validation checklist as PDF, Excel, or CSV.

    The checklist shows all extracted items with their verification status,
    grouped by category. Useful for auditing and sign-off purposes.
    """
    _get_drawing_with_access_check(drawing_id, db, current_user)

    try:
        export_format = ExportFormat(request.format)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid format. Must be one of: {[f.value for f in ExportFormat]}",
        )

    import uuid

    job_id = str(uuid.uuid4())
    _export_jobs[job_id] = {
        "status": "processing",
        "drawing_id": str(drawing_id),
        "export_type": "checklist",
        "file_path": None,
        "error": None,
    }

    background_tasks.add_task(
        _process_checklist_export,
        job_id,
        drawing_id,
        export_format,
        request.include_unverified,
    )

    return ExportJobResponse(
        job_id=job_id,
        drawing_id=str(drawing_id),
        export_type="checklist",
        status="processing",
        message="Validation checklist export job has been queued",
    )


async def _process_checklist_export(
    job_id: str,
    drawing_id: UUID,
    export_format: ExportFormat,
    include_unverified: bool,
) -> None:
    """Background task to process validation checklist export."""
    from app.core.database import SessionLocal

    logger.info(f"Starting checklist export for job {job_id}, drawing {drawing_id}")

    db = SessionLocal()
    try:
        drawing = db.query(Drawing).filter(Drawing.id == drawing_id).first()
        if not drawing:
            logger.error(f"Drawing {drawing_id} not found for job {job_id}")
            _export_jobs[job_id]["status"] = "failed"
            _export_jobs[job_id]["error"] = "Drawing not found"
            return

        logger.info(f"Found drawing: {drawing.original_filename}")
        symbols, lines, _ = _get_drawing_data(db, drawing_id)
        logger.info(f"Data: {len(symbols)} symbols, {len(lines)} lines")
        metadata = _create_export_metadata(drawing, db)

        service = DataListExportService()
        output_path = service.export_validation_checklist(
            drawing, symbols, lines, metadata, export_format, include_unverified
        )

        logger.info(f"Checklist export completed for job {job_id}: {output_path}")
        _export_jobs[job_id]["status"] = "completed"
        _export_jobs[job_id]["file_path"] = str(output_path)

    except Exception as e:
        logger.exception(f"Checklist export failed for job {job_id}: {e}")
        _export_jobs[job_id]["status"] = "failed"
        _export_jobs[job_id]["error"] = str(e)
    finally:
        db.close()


async def _process_report_export(
    job_id: str,
    drawing_id: UUID,
    export_format: ExportFormat,
) -> None:
    """Background task to process comparison report export."""
    from app.core.database import SessionLocal

    db = SessionLocal()
    try:
        drawing = db.query(Drawing).filter(Drawing.id == drawing_id).first()
        if not drawing:
            _export_jobs[job_id]["status"] = "failed"
            _export_jobs[job_id]["error"] = "Drawing not found"
            return

        symbols, lines, text_annotations = _get_drawing_data(db, drawing_id)
        metadata = _create_export_metadata(drawing, db)

        service = DataListExportService()
        output_path = service.export_comparison_report(
            drawing, symbols, lines, text_annotations, metadata, export_format
        )

        _export_jobs[job_id]["status"] = "completed"
        _export_jobs[job_id]["file_path"] = str(output_path)

    except Exception as e:
        logger.exception(f"Report export failed for job {job_id}")
        _export_jobs[job_id]["status"] = "failed"
        _export_jobs[job_id]["error"] = str(e)
    finally:
        db.close()


# Job Status and Download Endpoints


@router.get("/jobs/{job_id}/status", response_model=ExportStatusResponse)
async def get_export_status(
    job_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
) -> ExportStatusResponse:
    """Get the status of an export job."""
    job = _export_jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Export job not found")

    # Return status based on export type
    file_path = job.get("file_path")
    if not file_path and job.get("file_paths"):
        # For data list exports, return first file path
        paths = job.get("file_paths", {})
        file_path = next((p for p in paths.values() if not p.startswith("error")), None)

    return ExportStatusResponse(
        job_id=job_id,
        status=job["status"],
        file_path=file_path,
        error=job.get("error"),
    )


@router.get("/jobs/{job_id}/download")
async def download_export(
    job_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
    list_type: str = Query(default=None, description="List type for data list exports"),
) -> FileResponse:
    """Download the exported file."""
    logger.info(f"Download request for job {job_id}, list_type={list_type}")

    job = _export_jobs.get(job_id)
    if not job:
        logger.error(f"Job {job_id} not found in _export_jobs")
        raise HTTPException(status_code=404, detail="Export job not found")

    logger.info(f"Job {job_id} status: {job['status']}, file_path: {job.get('file_path')}, file_paths: {job.get('file_paths')}")

    if job["status"] != "completed":
        raise HTTPException(
            status_code=400,
            detail=f"Export job is not complete. Status: {job['status']}",
        )

    # Get file path
    file_path = None
    if job.get("file_path"):
        file_path = job["file_path"]
    elif job.get("file_paths"):
        if list_type:
            file_path = job["file_paths"].get(list_type)
            if file_path and file_path.startswith("error"):
                raise HTTPException(status_code=500, detail=file_path)
        else:
            # Return first successful file
            for path in job["file_paths"].values():
                if not path.startswith("error"):
                    file_path = path
                    break

    logger.info(f"Resolved file_path for job {job_id}: {file_path}")

    if not file_path:
        logger.error(f"No file path found for job {job_id}")
        raise HTTPException(status_code=404, detail="Export file not found")

    path = Path(file_path)
    if not path.exists():
        logger.error(f"File does not exist: {file_path}")
        raise HTTPException(status_code=404, detail="Export file not found on disk")

    # Determine content type
    content_type_map = {
        ".dxf": "application/dxf",
        ".dwg": "application/acad",
        ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        ".csv": "text/csv",
        ".pdf": "application/pdf",
        ".zip": "application/zip",
    }
    content_type = content_type_map.get(path.suffix, "application/octet-stream")

    return FileResponse(
        path=file_path,
        filename=path.name,
        media_type=content_type,
    )


@router.get("/jobs/{job_id}/files")
async def list_export_files(
    job_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
) -> dict[str, Any]:
    """List all files generated by a data list export job."""
    job = _export_jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Export job not found")

    if job["status"] != "completed":
        raise HTTPException(
            status_code=400,
            detail=f"Export job is not complete. Status: {job['status']}",
        )

    files = {}
    if job.get("file_path"):
        files["main"] = {
            "path": job["file_path"],
            "filename": Path(job["file_path"]).name,
        }
    elif job.get("file_paths"):
        for list_type, path in job["file_paths"].items():
            if path.startswith("error"):
                files[list_type] = {"error": path}
            else:
                files[list_type] = {
                    "path": path,
                    "filename": Path(path).name,
                }

    return {
        "job_id": job_id,
        "status": job["status"],
        "files": files,
    }

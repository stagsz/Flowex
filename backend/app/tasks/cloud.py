"""Celery tasks for cloud storage import/export operations."""

import asyncio
import logging
from io import BytesIO
from typing import Any
from uuid import UUID

from app.core.celery_app import celery_app
from app.core.database import AsyncSessionLocal, SessionLocal
from app.models import Drawing, DrawingStatus, Project
from app.services.cloud import CloudStorageService
from app.services.storage import get_storage_service

logger = logging.getLogger(__name__)


async def _import_file_async(
    connection_id: str,
    user_id: str,
    file_id: str,
    project_id: str,
    file_name: str,
) -> dict[str, Any]:
    """Async helper to import a single file."""
    async with AsyncSessionLocal() as db:
        service = CloudStorageService(db)

        # Download file from cloud
        content = await service.download_file(
            UUID(connection_id), UUID(user_id), file_id
        )

        return {"file_id": file_id, "file_name": file_name, "content": content}


async def _export_file_async(
    connection_id: str,
    user_id: str,
    folder_id: str,
    filename: str,
    content: bytes,
    mime_type: str,
) -> dict[str, Any]:
    """Async helper to export a single file."""
    async with AsyncSessionLocal() as db:
        service = CloudStorageService(db)

        # Check if file exists
        exists = await service.file_exists(
            UUID(connection_id), UUID(user_id), folder_id, filename
        )

        # Upload file to cloud
        cloud_file = await service.upload_file(
            UUID(connection_id),
            UUID(user_id),
            folder_id,
            filename,
            content,
            mime_type,
        )

        return {
            "filename": filename,
            "cloud_file_id": cloud_file.id,
            "overwritten": exists,
        }


async def _get_cloud_file_info(
    connection_id: str,
    user_id: str,
    file_ids: list[str],
) -> list[dict[str, Any]]:
    """Get file info for the files to import."""
    async with AsyncSessionLocal() as db:
        service = CloudStorageService(db)

        # We need to search/browse to get file names
        # For now, we'll download and use the cloud file info
        files = []
        for file_id in file_ids:
            try:
                # Download will give us the content
                content = await service.download_file(
                    UUID(connection_id), UUID(user_id), file_id
                )
                files.append({
                    "file_id": file_id,
                    "content": content,
                })
            except Exception as e:
                logger.error(f"Failed to download file {file_id}: {e}")
                files.append({
                    "file_id": file_id,
                    "error": str(e),
                })

        return files


@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)  # type: ignore[untyped-decorator]
def import_from_cloud(
    self: Any,
    connection_id: str,
    user_id: str,
    file_ids: list[str],
    project_id: str,
) -> dict[str, Any]:
    """
    Import files from cloud storage to a project.

    Args:
        connection_id: UUID of the cloud connection
        user_id: UUID of the user
        file_ids: List of cloud file IDs to import
        project_id: UUID of the project to import to

    Returns:
        Dict with import results
    """
    db = SessionLocal()

    try:
        # Verify project exists
        project = db.query(Project).filter(Project.id == UUID(project_id)).first()
        if not project:
            return {"error": "Project not found", "project_id": project_id}

        logger.info(
            f"Starting cloud import: {len(file_ids)} files to project {project_id}"
        )

        # Download files from cloud
        files = asyncio.run(_get_cloud_file_info(connection_id, user_id, file_ids))

        # Process each file
        imported = []
        errors = []
        storage = get_storage_service()

        for file_info in files:
            if "error" in file_info:
                errors.append(file_info)
                continue

            file_id = file_info["file_id"]
            content = file_info["content"]

            try:
                # Generate a filename (in real implementation, get from browse results)
                filename = f"cloud_import_{file_id[:8]}.pdf"

                # Upload to internal storage
                storage_path = f"projects/{project_id}/drawings/{filename}"
                asyncio.run(storage.upload_file(BytesIO(content), storage_path, "application/pdf"))

                # Create drawing record
                drawing = Drawing(
                    project_id=UUID(project_id),
                    original_filename=filename,
                    storage_path=storage_path,
                    file_size_bytes=len(content),
                    status=DrawingStatus.uploaded,
                )
                db.add(drawing)
                db.commit()
                db.refresh(drawing)

                imported.append({
                    "file_id": file_id,
                    "drawing_id": str(drawing.id),
                    "filename": filename,
                })

                logger.info(f"Imported file {file_id} as drawing {drawing.id}")

            except Exception as e:
                logger.error(f"Failed to process file {file_id}: {e}")
                errors.append({"file_id": file_id, "error": str(e)})

        result = {
            "status": "completed",
            "imported_count": len(imported),
            "error_count": len(errors),
            "imported": imported,
            "errors": errors,
        }

        logger.info(f"Cloud import completed: {result}")
        return result

    except Exception as e:
        logger.error(f"Cloud import failed: {e}")
        raise self.retry(exc=e)

    finally:
        db.close()


@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)  # type: ignore[untyped-decorator]
def export_to_cloud(
    self: Any,
    connection_id: str,
    user_id: str,
    drawing_id: str,
    folder_id: str,
    export_types: list[str],
) -> dict[str, Any]:
    """
    Export drawing files to cloud storage.

    Args:
        connection_id: UUID of the cloud connection
        user_id: UUID of the user
        drawing_id: UUID of the drawing to export
        folder_id: Cloud folder ID to export to
        export_types: List of export types (dwg, equipment_list, line_list, etc.)

    Returns:
        Dict with export results
    """
    db = SessionLocal()

    try:
        # Get drawing
        drawing = db.query(Drawing).filter(Drawing.id == UUID(drawing_id)).first()
        if not drawing:
            return {"error": "Drawing not found", "drawing_id": drawing_id}

        logger.info(
            f"Starting cloud export: drawing {drawing_id} with types {export_types}"
        )

        storage = get_storage_service()
        exported = []
        errors = []

        for export_type in export_types:
            try:
                # Determine file details based on export type
                if export_type == "dxf":
                    # Get DXF file from internal storage
                    dxf_path = f"projects/{drawing.project_id}/exports/{drawing_id}.dxf"
                    try:
                        content = asyncio.run(storage.download_file(dxf_path))
                        filename = f"{drawing.original_filename.replace('.pdf', '')}.dxf"
                        mime_type = "application/dxf"
                    except Exception:
                        errors.append({
                            "type": export_type,
                            "error": "DXF file not found. Generate export first.",
                        })
                        continue

                elif export_type == "equipment_list":
                    xlsx_path = f"projects/{drawing.project_id}/exports/{drawing_id}_equipment.xlsx"
                    try:
                        content = asyncio.run(storage.download_file(xlsx_path))
                        filename = f"{drawing.original_filename.replace('.pdf', '')}_Equipment-List.xlsx"
                        mime_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    except Exception:
                        errors.append({
                            "type": export_type,
                            "error": "Equipment list not found. Generate export first.",
                        })
                        continue

                elif export_type == "line_list":
                    xlsx_path = f"projects/{drawing.project_id}/exports/{drawing_id}_lines.xlsx"
                    try:
                        content = asyncio.run(storage.download_file(xlsx_path))
                        filename = f"{drawing.original_filename.replace('.pdf', '')}_Line-List.xlsx"
                        mime_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    except Exception:
                        errors.append({
                            "type": export_type,
                            "error": "Line list not found. Generate export first.",
                        })
                        continue

                elif export_type == "instrument_list":
                    xlsx_path = f"projects/{drawing.project_id}/exports/{drawing_id}_instruments.xlsx"
                    try:
                        content = asyncio.run(storage.download_file(xlsx_path))
                        filename = f"{drawing.original_filename.replace('.pdf', '')}_Instrument-List.xlsx"
                        mime_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    except Exception:
                        errors.append({
                            "type": export_type,
                            "error": "Instrument list not found. Generate export first.",
                        })
                        continue

                else:
                    errors.append({
                        "type": export_type,
                        "error": f"Unknown export type: {export_type}",
                    })
                    continue

                # Upload to cloud
                result = asyncio.run(
                    _export_file_async(
                        connection_id,
                        user_id,
                        folder_id,
                        filename,
                        content,
                        mime_type,
                    )
                )
                exported.append({
                    "type": export_type,
                    **result,
                })

                logger.info(f"Exported {export_type} as {filename}")

            except Exception as e:
                logger.error(f"Failed to export {export_type}: {e}")
                errors.append({"type": export_type, "error": str(e)})

        result = {
            "status": "completed",
            "exported_count": len(exported),
            "error_count": len(errors),
            "exported": exported,
            "errors": errors,
        }

        logger.info(f"Cloud export completed: {result}")
        return result

    except Exception as e:
        logger.error(f"Cloud export failed: {e}")
        raise self.retry(exc=e)

    finally:
        db.close()

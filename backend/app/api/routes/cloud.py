"""Cloud storage API routes."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, ConfigDict
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_async_db
from app.core.deps import get_current_user
from app.core.oauth_state import generate_oauth_state, validate_oauth_state
from app.models import User
from app.services.cloud import CloudStorageService

router = APIRouter(prefix="/cloud", tags=["cloud"])


# Pydantic schemas
class CloudConnectionResponse(BaseModel):
    """Response schema for cloud connection."""

    id: UUID
    provider: str
    account_email: str
    account_name: str | None
    site_name: str | None
    connected_at: str
    last_used_at: str | None

    model_config = ConfigDict(from_attributes=True)


class CloudFileResponse(BaseModel):
    """Response schema for cloud file."""

    id: str
    name: str
    path: str
    size: int
    mime_type: str
    modified_at: str
    thumbnail_url: str | None = None


class CloudFolderResponse(BaseModel):
    """Response schema for cloud folder."""

    id: str
    name: str
    path: str
    child_count: int = 0


class BrowseResponse(BaseModel):
    """Response schema for browse results."""

    current_folder: CloudFolderResponse | None
    folders: list[CloudFolderResponse]
    files: list[CloudFileResponse]


class ImportRequest(BaseModel):
    """Request schema for importing files from cloud."""

    file_ids: list[str]
    project_id: UUID


class ImportResponse(BaseModel):
    """Response schema for import job."""

    job_id: UUID
    status: str
    file_count: int


class ExportRequest(BaseModel):
    """Request schema for exporting files to cloud."""

    drawing_id: UUID
    folder_id: str
    files: list[str]


class ExportResponse(BaseModel):
    """Response schema for export job."""

    job_id: UUID
    status: str


class CreateFolderRequest(BaseModel):
    """Request schema for creating a folder."""

    parent_id: str
    name: str


class ConfigureSharePointRequest(BaseModel):
    """Request schema for configuring SharePoint."""

    site_id: str
    site_name: str
    drive_id: str


@router.get("/connections", response_model=list[CloudConnectionResponse])
async def list_connections(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_async_db)],
) -> list[CloudConnectionResponse]:
    """List all cloud connections for the current user."""
    service = CloudStorageService(db)
    connections = await service.get_connections(
        current_user.id, current_user.organization_id
    )

    return [
        CloudConnectionResponse(
            id=conn.id,
            provider=conn.provider.value,
            account_email=conn.account_email,
            account_name=conn.account_name,
            site_name=conn.site_name,
            connected_at=conn.created_at.isoformat(),
            last_used_at=conn.last_used_at.isoformat() if conn.last_used_at else None,
        )
        for conn in connections
    ]


@router.post("/connections/{provider}/connect")
async def initiate_connection(
    provider: str,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_async_db)],
) -> dict[str, str]:
    """Initiate OAuth connection to a cloud provider."""
    valid_providers = ["onedrive", "sharepoint", "google_drive", "microsoft", "google"]
    if provider not in valid_providers:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid provider. Must be one of: {', '.join(valid_providers)}",
        )

    # Generate and store state using centralized Redis-backed storage
    state = generate_oauth_state(
        current_user.id, current_user.organization_id, provider
    )

    service = CloudStorageService(db)
    auth_url = service.get_auth_url(provider, state)
    return {"auth_url": auth_url}


@router.get("/callback/{provider}")
async def oauth_callback(
    provider: str,
    code: str = Query(...),
    state: str = Query(...),
    db: AsyncSession = Depends(get_async_db),
) -> RedirectResponse:
    """Handle OAuth callback from cloud provider."""
    # Validate and consume state using centralized Redis-backed storage
    state_data = validate_oauth_state(state)
    if state_data is None:
        return RedirectResponse(
            url="/settings/integrations?error=invalid_state",
            status_code=status.HTTP_302_FOUND,
        )

    user_id = UUID(state_data["user_id"])
    org_id = UUID(state_data["org_id"])

    service = CloudStorageService(db)

    try:
        connection = await service.handle_oauth_callback(
            provider, code, user_id, org_id
        )
        return RedirectResponse(
            url=f"/settings/integrations?success=true&connection_id={connection.id}",
            status_code=status.HTTP_302_FOUND,
        )
    except Exception as e:
        return RedirectResponse(
            url=f"/settings/integrations?error={str(e)}",
            status_code=status.HTTP_302_FOUND,
        )


@router.delete("/connections/{connection_id}", status_code=status.HTTP_204_NO_CONTENT)
async def disconnect(
    connection_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_async_db)],
) -> None:
    """Disconnect a cloud storage connection."""
    service = CloudStorageService(db)
    deleted = await service.delete_connection(connection_id, current_user.id)

    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Connection not found",
        )


@router.get("/connections/{connection_id}/browse", response_model=BrowseResponse)
async def browse_folder(
    connection_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_async_db)],
    folder_id: str | None = Query(None),
) -> BrowseResponse:
    """Browse folder contents in cloud storage."""
    service = CloudStorageService(db)

    try:
        result = await service.browse(connection_id, current_user.id, folder_id)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        ) from e

    return BrowseResponse(
        current_folder=CloudFolderResponse(
            id=result.current_folder.id,
            name=result.current_folder.name,
            path=result.current_folder.path,
            child_count=result.current_folder.child_count,
        )
        if result.current_folder
        else None,
        folders=[
            CloudFolderResponse(
                id=f.id,
                name=f.name,
                path=f.path,
                child_count=f.child_count,
            )
            for f in result.folders
        ],
        files=[
            CloudFileResponse(
                id=f.id,
                name=f.name,
                path=f.path,
                size=f.size,
                mime_type=f.mime_type,
                modified_at=f.modified_at.isoformat(),
                thumbnail_url=f.thumbnail_url,
            )
            for f in result.files
        ],
    )


@router.get("/connections/{connection_id}/search", response_model=list[CloudFileResponse])
async def search_files(
    connection_id: UUID,
    query: str,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_async_db)],
    file_type: str | None = Query(None),
) -> list[CloudFileResponse]:
    """Search for files in cloud storage."""
    service = CloudStorageService(db)

    try:
        files = await service.search(connection_id, current_user.id, query, file_type)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        ) from e

    return [
        CloudFileResponse(
            id=f.id,
            name=f.name,
            path=f.path,
            size=f.size,
            mime_type=f.mime_type,
            modified_at=f.modified_at.isoformat(),
            thumbnail_url=f.thumbnail_url,
        )
        for f in files
    ]


@router.post("/connections/{connection_id}/import", response_model=ImportResponse)
async def import_files(
    connection_id: UUID,
    request: ImportRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_async_db)],
) -> ImportResponse:
    """Import files from cloud storage to a project."""
    from app.tasks.cloud import import_from_cloud

    # Verify connection exists
    service = CloudStorageService(db)
    connection = await service.get_connection(connection_id, current_user.id)
    if not connection:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Connection not found",
        )

    # Queue import task
    task = import_from_cloud.delay(
        str(connection_id),
        str(current_user.id),
        request.file_ids,
        str(request.project_id),
    )

    return ImportResponse(
        job_id=UUID(task.id),
        status="processing",
        file_count=len(request.file_ids),
    )


@router.post("/connections/{connection_id}/export", response_model=ExportResponse)
async def export_files(
    connection_id: UUID,
    request: ExportRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_async_db)],
) -> ExportResponse:
    """Export files to cloud storage."""
    from app.tasks.cloud import export_to_cloud

    # Verify connection exists
    service = CloudStorageService(db)
    connection = await service.get_connection(connection_id, current_user.id)
    if not connection:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Connection not found",
        )

    # Queue export task
    task = export_to_cloud.delay(
        str(connection_id),
        str(current_user.id),
        str(request.drawing_id),
        request.folder_id,
        request.files,
    )

    return ExportResponse(
        job_id=UUID(task.id),
        status="processing",
    )


@router.post(
    "/connections/{connection_id}/folders",
    response_model=CloudFolderResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_folder(
    connection_id: UUID,
    request: CreateFolderRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_async_db)],
) -> CloudFolderResponse:
    """Create a new folder in cloud storage."""
    service = CloudStorageService(db)

    try:
        folder = await service.create_folder(
            connection_id, current_user.id, request.parent_id, request.name
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        ) from e

    return CloudFolderResponse(
        id=folder.id,
        name=folder.name,
        path=folder.path,
        child_count=folder.child_count,
    )


@router.get("/connections/{connection_id}/sharepoint/sites")
async def list_sharepoint_sites(
    connection_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_async_db)],
) -> list[dict[str, str]]:
    """List available SharePoint sites."""
    service = CloudStorageService(db)

    try:
        sites = await service.get_sharepoint_sites(connection_id, current_user.id)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e

    return sites


@router.get("/connections/{connection_id}/sharepoint/sites/{site_id}/drives")
async def list_site_drives(
    connection_id: UUID,
    site_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_async_db)],
) -> list[dict[str, str]]:
    """List drives (document libraries) in a SharePoint site."""
    service = CloudStorageService(db)

    try:
        drives = await service.get_site_drives(connection_id, current_user.id, site_id)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e

    return drives


@router.post(
    "/connections/{connection_id}/sharepoint/configure",
    response_model=CloudConnectionResponse,
)
async def configure_sharepoint(
    connection_id: UUID,
    request: ConfigureSharePointRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_async_db)],
) -> CloudConnectionResponse:
    """Configure a connection for SharePoint."""
    service = CloudStorageService(db)

    try:
        connection = await service.configure_sharepoint(
            connection_id,
            current_user.id,
            request.site_id,
            request.site_name,
            request.drive_id,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        ) from e

    return CloudConnectionResponse(
        id=connection.id,
        provider=connection.provider.value,
        account_email=connection.account_email,
        account_name=connection.account_name,
        site_name=connection.site_name,
        connected_at=connection.created_at.isoformat(),
        last_used_at=connection.last_used_at.isoformat() if connection.last_used_at else None,
    )

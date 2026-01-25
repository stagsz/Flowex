from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict
from sqlalchemy import desc, func, or_
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.deps import get_current_user, get_db
from app.models import AuditAction, AuditLog, Drawing, EntityType, Project, User

router = APIRouter(prefix="/projects", tags=["projects"])


class ProjectCreate(BaseModel):
    name: str
    description: str | None = None


class ProjectUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    is_archived: bool | None = None


class ProjectResponse(BaseModel):
    id: str
    organization_id: str
    name: str
    description: str | None
    is_archived: bool
    created_at: str
    updated_at: str
    drawing_count: int = 0

    model_config = ConfigDict(from_attributes=True)


class ActivityItemResponse(BaseModel):
    """Single activity item in the project activity feed (DB-09)."""

    id: str
    user_name: str | None
    action: str
    entity_type: str | None
    entity_name: str | None
    timestamp: datetime

    model_config = ConfigDict(from_attributes=True)


class ActivityListResponse(BaseModel):
    """Paginated list of project activity items."""

    items: list[ActivityItemResponse]
    total: int
    limit: int


@router.get("/", response_model=list[ProjectResponse])
async def list_projects(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    skip: int = 0,
    limit: int = 100,
    include_archived: bool = False,
) -> list[ProjectResponse]:
    """List all projects for the current user's organization."""
    # In DEBUG mode, show all projects (for testing)
    if settings.DEBUG:
        query = db.query(Project)
    else:
        query = db.query(Project).filter(Project.organization_id == current_user.organization_id)
    if not include_archived:
        query = query.filter(Project.is_archived == False)  # noqa: E712
    projects = query.order_by(Project.created_at.desc()).offset(skip).limit(limit).all()

    # Get drawing counts for all projects in a single query
    project_ids = [p.id for p in projects]
    drawing_counts: dict[str, int] = {}
    if project_ids:
        counts = (
            db.query(Drawing.project_id, func.count(Drawing.id))
            .filter(Drawing.project_id.in_(project_ids))
            .group_by(Drawing.project_id)
            .all()
        )
        drawing_counts = {str(pid): count for pid, count in counts}

    return [
        ProjectResponse(
            id=str(p.id),
            organization_id=str(p.organization_id),
            name=p.name,
            description=p.description,
            is_archived=p.is_archived,
            created_at=p.created_at.isoformat(),
            updated_at=p.updated_at.isoformat(),
            drawing_count=drawing_counts.get(str(p.id), 0),
        )
        for p in projects
    ]


@router.post("/", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
async def create_project(
    project_data: ProjectCreate,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> ProjectResponse:
    """Create a new project."""
    project = Project(
        organization_id=current_user.organization_id,
        name=project_data.name,
        description=project_data.description,
    )
    db.add(project)
    db.commit()
    db.refresh(project)

    return ProjectResponse(
        id=str(project.id),
        organization_id=str(project.organization_id),
        name=project.name,
        description=project.description,
        is_archived=project.is_archived,
        created_at=project.created_at.isoformat(),
        updated_at=project.updated_at.isoformat(),
        drawing_count=0,  # New projects have no drawings
    )


@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(
    project_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> ProjectResponse:
    """Get a project by ID."""
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    if project.organization_id != current_user.organization_id:
        raise HTTPException(status_code=403, detail="Access denied")

    # Count drawings for this project
    drawing_count = db.query(func.count(Drawing.id)).filter(
        Drawing.project_id == project_id
    ).scalar() or 0

    return ProjectResponse(
        id=str(project.id),
        organization_id=str(project.organization_id),
        name=project.name,
        description=project.description,
        is_archived=project.is_archived,
        created_at=project.created_at.isoformat(),
        updated_at=project.updated_at.isoformat(),
        drawing_count=drawing_count,
    )


@router.patch("/{project_id}", response_model=ProjectResponse)
async def update_project(
    project_id: UUID,
    project_data: ProjectUpdate,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> ProjectResponse:
    """Update a project."""
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    if project.organization_id != current_user.organization_id:
        raise HTTPException(status_code=403, detail="Access denied")

    if project_data.name is not None:
        project.name = project_data.name
    if project_data.description is not None:
        project.description = project_data.description
    if project_data.is_archived is not None:
        project.is_archived = project_data.is_archived

    db.commit()
    db.refresh(project)

    # Count drawings for this project
    drawing_count = db.query(func.count(Drawing.id)).filter(
        Drawing.project_id == project_id
    ).scalar() or 0

    return ProjectResponse(
        id=str(project.id),
        organization_id=str(project.organization_id),
        name=project.name,
        description=project.description,
        is_archived=project.is_archived,
        created_at=project.created_at.isoformat(),
        updated_at=project.updated_at.isoformat(),
        drawing_count=drawing_count,
    )


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_project(
    project_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> None:
    """Delete a project (soft delete by archiving)."""
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    if project.organization_id != current_user.organization_id:
        raise HTTPException(status_code=403, detail="Access denied")

    project.is_archived = True
    db.commit()


# =============================================================================
# Activity Feed Endpoint (DB-09)
# =============================================================================

# Map AuditAction to user-friendly activity action names (per spec)
_ACTION_DISPLAY_MAP: dict[AuditAction, str] = {
    AuditAction.DRAWING_UPLOAD: "uploaded",
    AuditAction.DRAWING_PROCESS: "started_processing",
    AuditAction.DRAWING_DELETE: "deleted",
    AuditAction.SYMBOL_CREATE: "added_symbol",
    AuditAction.SYMBOL_UPDATE: "edited_symbol",
    AuditAction.SYMBOL_DELETE: "deleted_symbol",
    AuditAction.SYMBOL_VERIFY: "verified_symbol",
    AuditAction.SYMBOL_BULK_VERIFY: "completed_validation",
    AuditAction.SYMBOL_FLAG: "flagged_symbol",
    AuditAction.LINE_CREATE: "added_line",
    AuditAction.LINE_UPDATE: "edited_line",
    AuditAction.LINE_DELETE: "deleted_line",
    AuditAction.LINE_VERIFY: "verified_line",
    AuditAction.LINE_BULK_VERIFY: "verified_lines",
    AuditAction.EXPORT_DXF: "exported",
    AuditAction.EXPORT_LIST: "exported",
    AuditAction.EXPORT_REPORT: "exported",
    AuditAction.EXPORT_CHECKLIST: "exported",
    AuditAction.PROJECT_CREATE: "created_project",
    AuditAction.PROJECT_UPDATE: "updated_project",
    AuditAction.PROJECT_DELETE: "archived_project",
    AuditAction.USER_INVITE: "invited_user",
    AuditAction.USER_REMOVE: "removed_user",
}

# Entity types relevant to project activity
_PROJECT_ACTIVITY_ENTITY_TYPES = {
    EntityType.DRAWING,
    EntityType.SYMBOL,
    EntityType.LINE,
    EntityType.EXPORT_JOB,
    EntityType.PROJECT,
}


@router.get("/{project_id}/activity", response_model=ActivityListResponse)
async def get_project_activity(
    project_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    limit: int = Query(10, ge=1, le=100, description="Number of activity items to return"),
) -> ActivityListResponse:
    """Get recent activity feed for a project (DB-09).

    Returns a list of recent user activities related to the project,
    including uploads, validations, exports, and other drawing operations.

    Query parameters:
    - limit: Maximum number of items to return (default: 10, max: 100)
    """
    # Get project and verify access
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    if project.organization_id != current_user.organization_id:
        raise HTTPException(status_code=403, detail="Access denied")

    # Get all drawing IDs in this project for filtering
    drawing_ids = [
        d.id for d in db.query(Drawing.id).filter(Drawing.project_id == project_id).all()
    ]

    # Build query for activity logs
    # Include: project-level actions + drawing-related actions
    query = db.query(AuditLog).filter(
        AuditLog.organization_id == current_user.organization_id,
        AuditLog.entity_type.in_(_PROJECT_ACTIVITY_ENTITY_TYPES),
    )

    # Filter by project OR drawings within the project
    if drawing_ids:
        query = query.filter(
            or_(
                # Project-level actions
                (AuditLog.entity_type == EntityType.PROJECT)
                & (AuditLog.entity_id == project_id),
                # Drawing and related entity actions
                AuditLog.entity_id.in_(drawing_ids),
            )
        )
    else:
        # No drawings yet, only project-level actions
        query = query.filter(
            AuditLog.entity_type == EntityType.PROJECT,
            AuditLog.entity_id == project_id,
        )

    # Get total count
    total = query.count()

    # Get most recent activity items
    logs = query.order_by(desc(AuditLog.timestamp)).limit(limit).all()

    # Build drawing name lookup for entity names
    drawing_names: dict[UUID, str] = {}
    if drawing_ids:
        drawings = (
            db.query(Drawing.id, Drawing.original_filename)
            .filter(Drawing.id.in_(drawing_ids))
            .all()
        )
        drawing_names = {d.id: d.original_filename for d in drawings}

    # Transform logs to activity items
    items = []
    for log in logs:
        # Determine entity name
        entity_name: str | None = None
        if log.entity_type == EntityType.PROJECT:
            entity_name = project.name
        elif log.entity_type == EntityType.DRAWING and log.entity_id:
            entity_name = drawing_names.get(log.entity_id)
        elif log.entity_id:
            # For symbols/lines, try to get the drawing name from extra_data
            # or fall back to the entity ID
            if log.extra_data and "drawing_name" in log.extra_data:
                entity_name = log.extra_data["drawing_name"]
            elif log.extra_data and "drawing_id" in log.extra_data:
                drawing_id = UUID(log.extra_data["drawing_id"])
                entity_name = drawing_names.get(drawing_id)

        # Map action to display name
        action_display = _ACTION_DISPLAY_MAP.get(log.action, log.action.value)

        items.append(
            ActivityItemResponse(
                id=str(log.id),
                user_name=log.user.name if log.user else "System",
                action=action_display,
                entity_type=log.entity_type.value if log.entity_type else None,
                entity_name=entity_name,
                timestamp=log.timestamp,
            )
        )

    return ActivityListResponse(
        items=items,
        total=total,
        limit=limit,
    )

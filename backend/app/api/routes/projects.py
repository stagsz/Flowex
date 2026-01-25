from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict, EmailStr, Field
from sqlalchemy import desc, func, or_
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.deps import get_current_user, get_db
from app.models import (
    AuditAction,
    AuditLog,
    Drawing,
    EntityType,
    Project,
    ProjectMember,
    ProjectRole,
    User,
)

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
    """Create a new project.

    The creating user is automatically added as the project owner (PM-05).
    """
    project = Project(
        organization_id=current_user.organization_id,
        name=project_data.name,
        description=project_data.description,
    )
    db.add(project)
    db.flush()  # Get the project ID before creating membership

    # Add creator as project owner (PM-05)
    owner_membership = ProjectMember(
        project_id=project.id,
        user_id=current_user.id,
        role=ProjectRole.OWNER,
    )
    db.add(owner_membership)
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


# =============================================================================
# Project Member Management (PM-05)
# =============================================================================


class ProjectMemberResponse(BaseModel):
    """Project member information."""

    id: str
    user_id: str
    user_email: str
    user_name: str | None
    role: str
    added_at: datetime
    added_by_name: str | None

    model_config = ConfigDict(from_attributes=True)


class ProjectMemberListResponse(BaseModel):
    """Paginated list of project members."""

    items: list[ProjectMemberResponse]
    total: int
    page: int
    page_size: int


class AddProjectMemberRequest(BaseModel):
    """Request to add a user to a project."""

    user_id: str = Field(..., description="User ID to add to the project")
    role: ProjectRole = Field(default=ProjectRole.EDITOR, description="Role to assign")


class AddProjectMemberByEmailRequest(BaseModel):
    """Request to add a user to a project by email."""

    email: EmailStr = Field(..., description="Email address of the user to add")
    role: ProjectRole = Field(default=ProjectRole.EDITOR, description="Role to assign")


class UpdateProjectMemberRoleRequest(BaseModel):
    """Request to update a project member's role."""

    role: ProjectRole = Field(..., description="New role for the member")


def _serialize_project_member(member: ProjectMember) -> ProjectMemberResponse:
    """Serialize a project member for API response."""
    return ProjectMemberResponse(
        id=str(member.id),
        user_id=str(member.user_id),
        user_email=member.user.email,
        user_name=member.user.name,
        role=member.role.value,
        added_at=member.created_at,
        added_by_name=member.added_by.name if member.added_by else None,
    )


def _get_project_with_access_check(
    db: Session,
    project_id: UUID,
    current_user: User,
) -> Project:
    """Get a project and verify the user has access to it."""
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    if project.organization_id != current_user.organization_id:
        raise HTTPException(status_code=403, detail="Access denied")
    return project


def _get_user_project_role(db: Session, project_id: UUID, user_id: UUID) -> ProjectRole | None:
    """Get a user's role in a project, or None if not a member."""
    member = db.query(ProjectMember).filter(
        ProjectMember.project_id == project_id,
        ProjectMember.user_id == user_id,
    ).first()
    return member.role if member else None


def _require_project_owner(
    db: Session,
    project_id: UUID,
    current_user: User,
) -> None:
    """Require that the current user is the project owner."""
    role = _get_user_project_role(db, project_id, current_user.id)
    if role != ProjectRole.OWNER:
        raise HTTPException(
            status_code=403,
            detail="Only project owners can perform this action",
        )


@router.get("/{project_id}/members", response_model=ProjectMemberListResponse)
async def list_project_members(
    project_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
) -> ProjectMemberListResponse:
    """List all members of a project.

    All organization members can view the member list.
    """
    project = _get_project_with_access_check(db, project_id, current_user)

    # Build query
    query = db.query(ProjectMember).filter(ProjectMember.project_id == project.id)

    # Get total count
    total = query.count()

    # Get paginated results
    members = (
        query.order_by(ProjectMember.created_at)
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    return ProjectMemberListResponse(
        items=[_serialize_project_member(m) for m in members],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.post(
    "/{project_id}/members",
    response_model=ProjectMemberResponse,
    status_code=status.HTTP_201_CREATED,
)
async def add_project_member(
    project_id: UUID,
    body: AddProjectMemberRequest,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> ProjectMemberResponse:
    """Add a user to a project.

    Only project owners can add members.
    Users must be in the same organization as the project.
    """
    project = _get_project_with_access_check(db, project_id, current_user)
    _require_project_owner(db, project_id, current_user)

    # Parse user ID
    try:
        target_user_id = UUID(body.user_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid user ID format")

    # Find the target user
    target_user = db.query(User).filter(User.id == target_user_id).first()
    if not target_user:
        raise HTTPException(status_code=404, detail="User not found")

    # Verify user is in the same organization
    if target_user.organization_id != project.organization_id:
        raise HTTPException(
            status_code=400,
            detail="User must be in the same organization as the project",
        )

    # Check if already a member
    existing = db.query(ProjectMember).filter(
        ProjectMember.project_id == project_id,
        ProjectMember.user_id == target_user_id,
    ).first()
    if existing:
        raise HTTPException(
            status_code=400,
            detail="User is already a member of this project",
        )

    # Create membership
    member = ProjectMember(
        project_id=project_id,
        user_id=target_user_id,
        role=body.role,
        added_by_id=current_user.id,
    )
    db.add(member)
    db.commit()
    db.refresh(member)

    return _serialize_project_member(member)


@router.post(
    "/{project_id}/members/by-email",
    response_model=ProjectMemberResponse,
    status_code=status.HTTP_201_CREATED,
)
async def add_project_member_by_email(
    project_id: UUID,
    body: AddProjectMemberByEmailRequest,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> ProjectMemberResponse:
    """Add a user to a project by email address.

    Only project owners can add members.
    Users must be in the same organization as the project.
    """
    project = _get_project_with_access_check(db, project_id, current_user)
    _require_project_owner(db, project_id, current_user)

    # Find the target user by email
    target_user = db.query(User).filter(User.email == body.email).first()
    if not target_user:
        raise HTTPException(status_code=404, detail="User not found with this email")

    # Verify user is in the same organization
    if target_user.organization_id != project.organization_id:
        raise HTTPException(
            status_code=400,
            detail="User must be in the same organization as the project",
        )

    # Check if already a member
    existing = db.query(ProjectMember).filter(
        ProjectMember.project_id == project_id,
        ProjectMember.user_id == target_user.id,
    ).first()
    if existing:
        raise HTTPException(
            status_code=400,
            detail="User is already a member of this project",
        )

    # Create membership
    member = ProjectMember(
        project_id=project_id,
        user_id=target_user.id,
        role=body.role,
        added_by_id=current_user.id,
    )
    db.add(member)
    db.commit()
    db.refresh(member)

    return _serialize_project_member(member)


@router.patch(
    "/{project_id}/members/{member_id}",
    response_model=ProjectMemberResponse,
)
async def update_project_member_role(
    project_id: UUID,
    member_id: UUID,
    body: UpdateProjectMemberRoleRequest,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> ProjectMemberResponse:
    """Update a project member's role.

    Only project owners can update member roles.
    Cannot change the role of the last owner (prevents orphaned projects).
    """
    _get_project_with_access_check(db, project_id, current_user)
    _require_project_owner(db, project_id, current_user)

    # Find the membership
    member = db.query(ProjectMember).filter(
        ProjectMember.id == member_id,
        ProjectMember.project_id == project_id,
    ).first()
    if not member:
        raise HTTPException(status_code=404, detail="Project member not found")

    # Prevent removing the last owner
    if member.role == ProjectRole.OWNER and body.role != ProjectRole.OWNER:
        owner_count = db.query(ProjectMember).filter(
            ProjectMember.project_id == project_id,
            ProjectMember.role == ProjectRole.OWNER,
        ).count()
        if owner_count <= 1:
            raise HTTPException(
                status_code=400,
                detail="Cannot change the last owner's role. Assign another owner first.",
            )

    member.role = body.role
    db.commit()
    db.refresh(member)

    return _serialize_project_member(member)


@router.delete(
    "/{project_id}/members/{member_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def remove_project_member(
    project_id: UUID,
    member_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> None:
    """Remove a user from a project.

    Only project owners can remove members.
    Cannot remove the last owner (prevents orphaned projects).
    Users can remove themselves unless they are the last owner.
    """
    _get_project_with_access_check(db, project_id, current_user)

    # Find the membership
    member = db.query(ProjectMember).filter(
        ProjectMember.id == member_id,
        ProjectMember.project_id == project_id,
    ).first()
    if not member:
        raise HTTPException(status_code=404, detail="Project member not found")

    # Check permissions: owner can remove anyone, users can remove themselves
    current_user_role = _get_user_project_role(db, project_id, current_user.id)
    is_self = member.user_id == current_user.id

    if not is_self and current_user_role != ProjectRole.OWNER:
        raise HTTPException(
            status_code=403,
            detail="Only project owners can remove other members",
        )

    # Prevent removing the last owner
    if member.role == ProjectRole.OWNER:
        owner_count = db.query(ProjectMember).filter(
            ProjectMember.project_id == project_id,
            ProjectMember.role == ProjectRole.OWNER,
        ).count()
        if owner_count <= 1:
            raise HTTPException(
                status_code=400,
                detail="Cannot remove the last owner. Assign another owner first.",
            )

    db.delete(member)
    db.commit()


@router.get("/{project_id}/members/me", response_model=ProjectMemberResponse | None)
async def get_my_project_membership(
    project_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> ProjectMemberResponse | None:
    """Get the current user's membership in a project.

    Returns the membership details if the user is a member, or null if not.
    Useful for checking permissions in the frontend.
    """
    project = _get_project_with_access_check(db, project_id, current_user)

    member = db.query(ProjectMember).filter(
        ProjectMember.project_id == project.id,
        ProjectMember.user_id == current_user.id,
    ).first()

    if not member:
        return None

    return _serialize_project_member(member)

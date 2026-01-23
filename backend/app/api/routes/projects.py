from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.deps import get_current_user, get_db
from app.models import Drawing, Project, User

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

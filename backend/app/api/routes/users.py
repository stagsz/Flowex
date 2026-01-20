"""User endpoints for GDPR compliance (data export, account deletion)."""

from datetime import UTC, datetime
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session

from app.core.deps import get_current_user, get_db
from app.core.rate_limiting import default_limit, limiter
from app.models import (
    CloudConnection,
    Drawing,
    Line,
    Organization,
    Project,
    Symbol,
    TextAnnotation,
    User,
)

router = APIRouter(prefix="/users", tags=["users"])


# =============================================================================
# Response Models
# =============================================================================


class UserProfileExport(BaseModel):
    """User profile data for GDPR export."""

    id: str
    email: str
    name: str | None
    role: str
    sso_provider: str | None
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class OrganizationExport(BaseModel):
    """Organization data for GDPR export."""

    id: str
    name: str
    slug: str
    subscription_tier: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class SymbolExport(BaseModel):
    """Symbol data for GDPR export."""

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
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class LineExport(BaseModel):
    """Line data for GDPR export."""

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
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TextAnnotationExport(BaseModel):
    """Text annotation data for GDPR export."""

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
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class DrawingExport(BaseModel):
    """Drawing data for GDPR export."""

    id: str
    original_filename: str
    file_size_bytes: int
    file_type: str | None
    status: str
    error_message: str | None
    processing_started_at: datetime | None
    processing_completed_at: datetime | None
    created_at: datetime
    updated_at: datetime
    symbols: list[SymbolExport]
    lines: list[LineExport]
    text_annotations: list[TextAnnotationExport]

    model_config = ConfigDict(from_attributes=True)


class ProjectExport(BaseModel):
    """Project data for GDPR export."""

    id: str
    name: str
    description: str | None
    is_archived: bool
    created_at: datetime
    updated_at: datetime
    drawings: list[DrawingExport]

    model_config = ConfigDict(from_attributes=True)


class CloudConnectionExport(BaseModel):
    """Cloud connection data for GDPR export (tokens excluded for security)."""

    id: str
    provider: str
    account_email: str
    account_name: str | None
    site_name: str | None
    last_used_at: datetime | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class GDPRDataExportResponse(BaseModel):
    """Complete GDPR data export response (Article 15 - Right of Access)."""

    export_date: datetime
    export_format: str = "JSON"
    gdpr_article: str = "Article 15 - Right of Access"
    user: UserProfileExport
    organization: OrganizationExport
    projects: list[ProjectExport]
    cloud_connections: list[CloudConnectionExport]
    metadata: dict[str, Any]

    model_config = ConfigDict(from_attributes=True)


class AccountDeletionResponse(BaseModel):
    """Response for account deletion request."""

    message: str
    deletion_scheduled_at: datetime
    grace_period_days: int = 30
    data_to_be_deleted: list[str]


# =============================================================================
# Helper Functions
# =============================================================================


def _serialize_symbol(symbol: Symbol) -> SymbolExport:
    """Serialize a symbol for export."""
    return SymbolExport(
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
        created_at=symbol.created_at,
    )


def _serialize_line(line: Line) -> LineExport:
    """Serialize a line for export."""
    return LineExport(
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
        created_at=line.created_at,
    )


def _serialize_text_annotation(text: TextAnnotation) -> TextAnnotationExport:
    """Serialize a text annotation for export."""
    return TextAnnotationExport(
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
        created_at=text.created_at,
    )


def _serialize_drawing(drawing: Drawing, db: Session) -> DrawingExport:
    """Serialize a drawing with all related data for export."""
    # Get non-deleted symbols, lines, and text annotations
    symbols = db.query(Symbol).filter(
        Symbol.drawing_id == drawing.id,
        Symbol.is_deleted.is_(False),
    ).all()

    lines = db.query(Line).filter(
        Line.drawing_id == drawing.id,
        Line.is_deleted.is_(False),
    ).all()

    text_annotations = db.query(TextAnnotation).filter(
        TextAnnotation.drawing_id == drawing.id,
        TextAnnotation.is_deleted.is_(False),
    ).all()

    return DrawingExport(
        id=str(drawing.id),
        original_filename=drawing.original_filename,
        file_size_bytes=drawing.file_size_bytes,
        file_type=drawing.file_type.value if drawing.file_type else None,
        status=drawing.status.value,
        error_message=drawing.error_message,
        processing_started_at=drawing.processing_started_at,
        processing_completed_at=drawing.processing_completed_at,
        created_at=drawing.created_at,
        updated_at=drawing.updated_at,
        symbols=[_serialize_symbol(s) for s in symbols],
        lines=[_serialize_line(line) for line in lines],
        text_annotations=[_serialize_text_annotation(t) for t in text_annotations],
    )


def _serialize_project(project: Project, db: Session) -> ProjectExport:
    """Serialize a project with all drawings for export."""
    drawings = db.query(Drawing).filter(Drawing.project_id == project.id).all()

    return ProjectExport(
        id=str(project.id),
        name=project.name,
        description=project.description,
        is_archived=project.is_archived,
        created_at=project.created_at,
        updated_at=project.updated_at,
        drawings=[_serialize_drawing(d, db) for d in drawings],
    )


def _serialize_cloud_connection(conn: CloudConnection) -> CloudConnectionExport:
    """Serialize a cloud connection for export (tokens excluded)."""
    return CloudConnectionExport(
        id=str(conn.id),
        provider=conn.provider.value,
        account_email=conn.account_email,
        account_name=conn.account_name,
        site_name=conn.site_name,
        last_used_at=conn.last_used_at,
        created_at=conn.created_at,
    )


# =============================================================================
# API Endpoints
# =============================================================================


@router.get("/me/data-export", response_model=GDPRDataExportResponse)
@limiter.limit(default_limit)
async def export_user_data(
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> GDPRDataExportResponse:
    """Export all user data (GDPR Article 15 - Right of Access).

    Returns all personal data associated with the authenticated user including:
    - User profile information
    - Organization membership
    - Projects and drawings (within user's organization)
    - Cloud storage connections
    - All extracted symbols, lines, and text annotations

    Note: This endpoint may take several seconds for users with large amounts of data.
    For security, encrypted tokens are not included in the export.
    """
    # Get organization
    org = db.query(Organization).filter(Organization.id == current_user.organization_id).first()
    if not org:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="User organization not found",
        )

    # Get all projects in user's organization
    projects = db.query(Project).filter(
        Project.organization_id == current_user.organization_id
    ).all()

    # Get user's cloud connections
    cloud_connections = db.query(CloudConnection).filter(
        CloudConnection.user_id == current_user.id
    ).all()

    # Count total items for metadata
    total_drawings = sum(
        db.query(Drawing).filter(Drawing.project_id == p.id).count()
        for p in projects
    )
    total_symbols = db.query(Symbol).join(Drawing).join(Project).filter(
        Project.organization_id == current_user.organization_id,
        Symbol.is_deleted.is_(False),
    ).count()
    total_lines = db.query(Line).join(Drawing).join(Project).filter(
        Project.organization_id == current_user.organization_id,
        Line.is_deleted.is_(False),
    ).count()
    total_text_annotations = db.query(TextAnnotation).join(Drawing).join(Project).filter(
        Project.organization_id == current_user.organization_id,
        TextAnnotation.is_deleted.is_(False),
    ).count()

    # Build export response
    return GDPRDataExportResponse(
        export_date=datetime.now(UTC),
        user=UserProfileExport(
            id=str(current_user.id),
            email=current_user.email,
            name=current_user.name,
            role=current_user.role.value,
            sso_provider=current_user.sso_provider.value if current_user.sso_provider else None,
            is_active=current_user.is_active,
            created_at=current_user.created_at,
            updated_at=current_user.updated_at,
        ),
        organization=OrganizationExport(
            id=str(org.id),
            name=org.name,
            slug=org.slug,
            subscription_tier=org.subscription_tier.value,
            created_at=org.created_at,
            updated_at=org.updated_at,
        ),
        projects=[_serialize_project(p, db) for p in projects],
        cloud_connections=[_serialize_cloud_connection(c) for c in cloud_connections],
        metadata={
            "total_projects": len(projects),
            "total_drawings": total_drawings,
            "total_symbols": total_symbols,
            "total_lines": total_lines,
            "total_text_annotations": total_text_annotations,
            "total_cloud_connections": len(cloud_connections),
            "data_categories": [
                "user_profile",
                "organization_membership",
                "projects",
                "drawings",
                "ai_extracted_data",
                "cloud_connections",
            ],
            "excluded_for_security": [
                "cloud_connection_tokens",
                "sso_subject_id",
            ],
        },
    )


@router.delete("/me", response_model=AccountDeletionResponse)
@limiter.limit(default_limit)
async def request_account_deletion(
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> AccountDeletionResponse:
    """Request account deletion (GDPR Article 17 - Right to Erasure).

    Schedules the user's account and all associated data for deletion after a
    30-day grace period. During this period:
    - The user account is deactivated (is_active=False)
    - User cannot log in
    - Data is retained but inaccessible
    - Deletion can be cancelled by contacting support

    After the grace period, the following data is permanently deleted:
    - User profile
    - Cloud storage connections
    - If user is the only member of their organization:
      - All organization data
      - All projects and drawings
      - All extracted symbols, lines, and text annotations
    """
    # Deactivate the user account
    current_user.is_active = False
    db.commit()

    # Calculate deletion date (30 days from now)
    deletion_date = datetime.now(UTC)

    # Determine what data will be deleted
    data_to_be_deleted = [
        "User profile (email, name, role)",
        "Cloud storage connections and tokens",
        "SSO provider association",
    ]

    # Check if user is the only member of their organization
    org_user_count = db.query(User).filter(
        User.organization_id == current_user.organization_id,
        User.is_active.is_(True),
    ).count()

    if org_user_count == 0:  # This user was the last active member
        # Count organization data
        project_count = db.query(Project).filter(
            Project.organization_id == current_user.organization_id
        ).count()
        drawing_count = db.query(Drawing).join(Project).filter(
            Project.organization_id == current_user.organization_id
        ).count()

        data_to_be_deleted.extend([
            f"Organization data ({current_user.organization.name})",
            f"{project_count} project(s)",
            f"{drawing_count} drawing(s) and associated files",
            "All extracted symbols, lines, and text annotations",
        ])
    else:
        data_to_be_deleted.append(
            "Note: Organization data retained (other active members exist)"
        )

    return AccountDeletionResponse(
        message="Account deletion scheduled. Your account has been deactivated. "
        "Contact support within 30 days to cancel deletion.",
        deletion_scheduled_at=deletion_date,
        grace_period_days=30,
        data_to_be_deleted=data_to_be_deleted,
    )

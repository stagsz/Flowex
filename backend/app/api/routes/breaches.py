"""Security breach management endpoints for GDPR Article 33 compliance.

GDPR Article 33 requires:
- Notification to supervisory authority within 72 hours of breach detection
- Documentation of all breaches (even if not notified)
- Notification to affected data subjects if high risk (Article 34)
"""

from datetime import UTC, datetime, timedelta
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.core.deps import get_db, require_admin
from app.core.rate_limiting import default_limit, limiter
from app.models import AuditAction, EntityType, User
from app.models.security_breach import (
    BreachCategory,
    BreachSeverity,
    BreachStatus,
    SecurityBreach,
)
from app.services.audit import log_action

router = APIRouter(prefix="/breaches", tags=["security-breaches"])


# =============================================================================
# Request/Response Models
# =============================================================================


class CreateBreachRequest(BaseModel):
    """Request to report a security breach."""

    title: str = Field(..., min_length=5, max_length=200, description="Brief title of the breach")
    description: str = Field(..., min_length=20, description="Detailed description of the incident")
    severity: BreachSeverity = Field(default=BreachSeverity.MEDIUM, description="Severity level")
    category: BreachCategory = Field(
        default=BreachCategory.CONFIDENTIALITY, description="Type of breach"
    )
    detected_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC), description="When breach was detected"
    )
    affected_users_count: int = Field(default=0, ge=0, description="Number of affected users")
    data_categories_affected: list[str] | None = Field(
        default=None, description="Categories of data affected (e.g., email, drawings)"
    )


class UpdateBreachRequest(BaseModel):
    """Request to update a security breach."""

    title: str | None = Field(default=None, max_length=200)
    description: str | None = None
    severity: BreachSeverity | None = None
    status: BreachStatus | None = None
    category: BreachCategory | None = None
    contained_at: datetime | None = None
    resolved_at: datetime | None = None
    affected_users_count: int | None = Field(default=None, ge=0)
    data_categories_affected: list[str] | None = None
    root_cause: str | None = None
    remediation_steps: str | None = None
    preventive_measures: str | None = None


class NotifyAuthorityRequest(BaseModel):
    """Request to record authority notification."""

    authority_reference: str | None = Field(
        default=None, max_length=100, description="Reference number from authority"
    )
    notes: str | None = Field(default=None, description="Additional notes about notification")


class NotifyUsersRequest(BaseModel):
    """Request to record user notification."""

    notification_method: str = Field(..., description="How users were notified (email, in-app, etc.)")
    message_summary: str | None = Field(default=None, description="Summary of notification message")


class BreachResponse(BaseModel):
    """Security breach information."""

    id: str
    title: str
    description: str
    severity: str
    status: str
    category: str
    detected_at: datetime
    contained_at: datetime | None
    resolved_at: datetime | None
    affected_users_count: int
    data_categories_affected: list[str] | None
    authority_notified: bool
    authority_notified_at: datetime | None
    authority_reference: str | None
    users_notified: bool
    users_notified_at: datetime | None
    root_cause: str | None
    remediation_steps: str | None
    preventive_measures: str | None
    reported_by_id: str | None
    reported_by_name: str | None
    hours_since_detection: float
    notification_deadline: datetime  # 72 hours from detection
    is_past_notification_deadline: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class BreachListResponse(BaseModel):
    """Paginated list of security breaches."""

    items: list[BreachResponse]
    total: int
    page: int
    page_size: int


class BreachStatsResponse(BaseModel):
    """Statistics for breach dashboard."""

    total_breaches: int
    open_breaches: int  # Not resolved
    critical_breaches: int
    breaches_pending_authority_notification: int
    breaches_past_deadline: int  # Over 72 hours without authority notification
    average_time_to_containment_hours: float | None
    average_time_to_resolution_hours: float | None


# =============================================================================
# Helper Functions
# =============================================================================


def _serialize_breach(breach: SecurityBreach) -> BreachResponse:
    """Serialize a breach for API response."""
    now = datetime.now(UTC)
    hours_since_detection = (now - breach.detected_at).total_seconds() / 3600
    notification_deadline = breach.detected_at + timedelta(hours=72)
    is_past_deadline = now > notification_deadline and not breach.authority_notified

    return BreachResponse(
        id=str(breach.id),
        title=breach.title,
        description=breach.description,
        severity=breach.severity.value,
        status=breach.status.value,
        category=breach.category.value,
        detected_at=breach.detected_at,
        contained_at=breach.contained_at,
        resolved_at=breach.resolved_at,
        affected_users_count=breach.affected_users_count,
        data_categories_affected=breach.data_categories_affected,
        authority_notified=breach.authority_notified,
        authority_notified_at=breach.authority_notified_at,
        authority_reference=breach.authority_reference,
        users_notified=breach.users_notified,
        users_notified_at=breach.users_notified_at,
        root_cause=breach.root_cause,
        remediation_steps=breach.remediation_steps,
        preventive_measures=breach.preventive_measures,
        reported_by_id=str(breach.reported_by_id) if breach.reported_by_id else None,
        reported_by_name=breach.reported_by.name if breach.reported_by else None,
        hours_since_detection=round(hours_since_detection, 1),
        notification_deadline=notification_deadline,
        is_past_notification_deadline=is_past_deadline,
        created_at=breach.created_at,
        updated_at=breach.updated_at,
    )


# =============================================================================
# API Endpoints
# =============================================================================


@router.post("", response_model=BreachResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit(default_limit)
async def report_breach(
    request: Request,
    body: CreateBreachRequest,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_admin)],
) -> BreachResponse:
    """Report a new security breach (GDPR Article 33).

    Admin only. Creates a new breach record in the system.
    Note: GDPR requires notification to supervisory authority within 72 hours
    of becoming aware of a breach that poses a risk to individuals.
    """
    breach = SecurityBreach(
        organization_id=current_user.organization_id,
        reported_by_id=current_user.id,
        title=body.title,
        description=body.description,
        severity=body.severity,
        status=BreachStatus.DETECTED,
        category=body.category,
        detected_at=body.detected_at,
        affected_users_count=body.affected_users_count,
        data_categories_affected=body.data_categories_affected,
    )
    db.add(breach)
    db.flush()  # Get the breach ID

    # Log the action
    log_action(
        db=db,
        user=current_user,
        organization_id=current_user.organization_id,
        action=AuditAction.BREACH_REPORTED,
        request=request,
        entity_type=EntityType.SECURITY_BREACH,
        entity_id=breach.id,
        metadata={
            "breach_title": body.title,
            "severity": body.severity.value,
            "category": body.category.value,
            "affected_users_count": str(body.affected_users_count),
        },
    )

    db.commit()
    db.refresh(breach)

    return _serialize_breach(breach)


@router.get("", response_model=BreachListResponse)
@limiter.limit(default_limit)
async def list_breaches(
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_admin)],
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status_filter: BreachStatus | None = Query(None, alias="status"),
    severity_filter: BreachSeverity | None = Query(None, alias="severity"),
    show_resolved: bool = Query(True, description="Include resolved breaches"),
) -> BreachListResponse:
    """List all security breaches for the organization.

    Admin only. Returns a paginated list of breach records.
    """
    query = db.query(SecurityBreach).filter(
        SecurityBreach.organization_id == current_user.organization_id
    )

    # Apply filters
    if status_filter:
        query = query.filter(SecurityBreach.status == status_filter)
    if severity_filter:
        query = query.filter(SecurityBreach.severity == severity_filter)
    if not show_resolved:
        query = query.filter(SecurityBreach.status != BreachStatus.RESOLVED)

    # Get total count
    total = query.count()

    # Get paginated results (most recent first)
    breaches = (
        query.order_by(desc(SecurityBreach.detected_at))
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    return BreachListResponse(
        items=[_serialize_breach(b) for b in breaches],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/stats", response_model=BreachStatsResponse)
@limiter.limit(default_limit)
async def get_breach_stats(
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_admin)],
) -> BreachStatsResponse:
    """Get breach statistics for the organization dashboard.

    Admin only. Returns summary statistics for breach monitoring.
    """
    now = datetime.now(UTC)
    deadline_threshold = now - timedelta(hours=72)

    breaches = db.query(SecurityBreach).filter(
        SecurityBreach.organization_id == current_user.organization_id
    ).all()

    total = len(breaches)
    open_breaches = sum(1 for b in breaches if b.status != BreachStatus.RESOLVED)
    critical = sum(1 for b in breaches if b.severity == BreachSeverity.CRITICAL)

    # Breaches that need authority notification (not notified, not low severity)
    pending_notification = sum(
        1 for b in breaches
        if not b.authority_notified
        and b.status != BreachStatus.RESOLVED
        and b.severity != BreachSeverity.LOW
    )

    # Breaches past the 72-hour notification deadline
    past_deadline = sum(
        1 for b in breaches
        if not b.authority_notified
        and b.detected_at < deadline_threshold
        and b.status != BreachStatus.RESOLVED
        and b.severity != BreachSeverity.LOW
    )

    # Calculate average time to containment
    contained = [
        b for b in breaches
        if b.contained_at is not None and b.detected_at is not None
    ]
    avg_containment = None
    if contained:
        containment_times = [
            (b.contained_at - b.detected_at).total_seconds() / 3600  # type: ignore[operator]
            for b in contained
        ]
        avg_containment = round(sum(containment_times) / len(containment_times), 1)

    # Calculate average time to resolution
    resolved = [
        b for b in breaches
        if b.resolved_at is not None and b.detected_at is not None
    ]
    avg_resolution = None
    if resolved:
        resolution_times = [
            (b.resolved_at - b.detected_at).total_seconds() / 3600  # type: ignore[operator]
            for b in resolved
        ]
        avg_resolution = round(sum(resolution_times) / len(resolution_times), 1)

    return BreachStatsResponse(
        total_breaches=total,
        open_breaches=open_breaches,
        critical_breaches=critical,
        breaches_pending_authority_notification=pending_notification,
        breaches_past_deadline=past_deadline,
        average_time_to_containment_hours=avg_containment,
        average_time_to_resolution_hours=avg_resolution,
    )


@router.get("/{breach_id}", response_model=BreachResponse)
@limiter.limit(default_limit)
async def get_breach(
    request: Request,
    breach_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_admin)],
) -> BreachResponse:
    """Get a specific security breach by ID.

    Admin only. Returns detailed breach information.
    """
    breach = db.query(SecurityBreach).filter(
        SecurityBreach.id == breach_id,
        SecurityBreach.organization_id == current_user.organization_id,
    ).first()

    if not breach:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Breach not found",
        )

    return _serialize_breach(breach)


@router.patch("/{breach_id}", response_model=BreachResponse)
@limiter.limit(default_limit)
async def update_breach(
    request: Request,
    breach_id: UUID,
    body: UpdateBreachRequest,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_admin)],
) -> BreachResponse:
    """Update a security breach record.

    Admin only. Updates breach details, status, and investigation findings.
    """
    breach = db.query(SecurityBreach).filter(
        SecurityBreach.id == breach_id,
        SecurityBreach.organization_id == current_user.organization_id,
    ).first()

    if not breach:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Breach not found",
        )

    # Track changes for audit log
    changes: dict[str, str] = {}

    # Update fields if provided
    if body.title is not None:
        changes["title"] = f"{breach.title} -> {body.title}"
        breach.title = body.title
    if body.description is not None:
        changes["description"] = "updated"
        breach.description = body.description
    if body.severity is not None:
        changes["severity"] = f"{breach.severity.value} -> {body.severity.value}"
        breach.severity = body.severity
    if body.status is not None:
        changes["status"] = f"{breach.status.value} -> {body.status.value}"
        breach.status = body.status
        if body.status == BreachStatus.RESOLVED and breach.resolved_at is None:
            breach.resolved_at = datetime.now(UTC)
    if body.category is not None:
        changes["category"] = f"{breach.category.value} -> {body.category.value}"
        breach.category = body.category
    if body.contained_at is not None:
        breach.contained_at = body.contained_at
        changes["contained_at"] = str(body.contained_at)
    if body.resolved_at is not None:
        breach.resolved_at = body.resolved_at
        changes["resolved_at"] = str(body.resolved_at)
    if body.affected_users_count is not None:
        changes["affected_users_count"] = f"{breach.affected_users_count} -> {body.affected_users_count}"
        breach.affected_users_count = body.affected_users_count
    if body.data_categories_affected is not None:
        breach.data_categories_affected = body.data_categories_affected
        changes["data_categories_affected"] = "updated"
    if body.root_cause is not None:
        breach.root_cause = body.root_cause
        changes["root_cause"] = "updated"
    if body.remediation_steps is not None:
        breach.remediation_steps = body.remediation_steps
        changes["remediation_steps"] = "updated"
    if body.preventive_measures is not None:
        breach.preventive_measures = body.preventive_measures
        changes["preventive_measures"] = "updated"

    # Log the action
    log_action(
        db=db,
        user=current_user,
        organization_id=current_user.organization_id,
        action=AuditAction.BREACH_UPDATED,
        request=request,
        entity_type=EntityType.SECURITY_BREACH,
        entity_id=breach_id,
        metadata=changes,
    )

    db.commit()
    db.refresh(breach)

    return _serialize_breach(breach)


@router.post("/{breach_id}/notify-authority", response_model=BreachResponse)
@limiter.limit(default_limit)
async def notify_authority(
    request: Request,
    breach_id: UUID,
    body: NotifyAuthorityRequest,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_admin)],
) -> BreachResponse:
    """Record that supervisory authority has been notified (GDPR Article 33).

    Admin only. Marks the breach as having been reported to the data protection
    authority and records the reference number if provided.
    """
    breach = db.query(SecurityBreach).filter(
        SecurityBreach.id == breach_id,
        SecurityBreach.organization_id == current_user.organization_id,
    ).first()

    if not breach:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Breach not found",
        )

    if breach.authority_notified:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Authority has already been notified for this breach",
        )

    # Update breach record
    breach.authority_notified = True
    breach.authority_notified_at = datetime.now(UTC)
    breach.authority_reference = body.authority_reference

    # Update status if still in early stages
    if breach.status in (BreachStatus.DETECTED, BreachStatus.INVESTIGATING):
        breach.status = BreachStatus.NOTIFYING

    # Log the action
    log_action(
        db=db,
        user=current_user,
        organization_id=current_user.organization_id,
        action=AuditAction.BREACH_AUTHORITY_NOTIFIED,
        request=request,
        entity_type=EntityType.SECURITY_BREACH,
        entity_id=breach_id,
        metadata={
            "breach_title": breach.title,
            "authority_reference": body.authority_reference or "none",
            "hours_since_detection": str(
                round((datetime.now(UTC) - breach.detected_at).total_seconds() / 3600, 1)
            ),
        },
    )

    db.commit()
    db.refresh(breach)

    return _serialize_breach(breach)


@router.post("/{breach_id}/notify-users", response_model=BreachResponse)
@limiter.limit(default_limit)
async def notify_users(
    request: Request,
    breach_id: UUID,
    body: NotifyUsersRequest,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_admin)],
) -> BreachResponse:
    """Record that affected users have been notified (GDPR Article 34).

    Admin only. GDPR Article 34 requires notification to affected data subjects
    when a breach is likely to result in high risk to their rights and freedoms.
    """
    breach = db.query(SecurityBreach).filter(
        SecurityBreach.id == breach_id,
        SecurityBreach.organization_id == current_user.organization_id,
    ).first()

    if not breach:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Breach not found",
        )

    if breach.users_notified:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Users have already been notified for this breach",
        )

    # Update breach record
    breach.users_notified = True
    breach.users_notified_at = datetime.now(UTC)

    # Log the action
    log_action(
        db=db,
        user=current_user,
        organization_id=current_user.organization_id,
        action=AuditAction.BREACH_USERS_NOTIFIED,
        request=request,
        entity_type=EntityType.SECURITY_BREACH,
        entity_id=breach_id,
        metadata={
            "breach_title": breach.title,
            "notification_method": body.notification_method,
            "affected_users_count": str(breach.affected_users_count),
            "message_summary": body.message_summary or "none",
        },
    )

    db.commit()
    db.refresh(breach)

    return _serialize_breach(breach)


@router.post("/{breach_id}/resolve", response_model=BreachResponse)
@limiter.limit(default_limit)
async def resolve_breach(
    request: Request,
    breach_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_admin)],
) -> BreachResponse:
    """Mark a security breach as resolved.

    Admin only. Sets the breach status to resolved and records the resolution time.
    """
    breach = db.query(SecurityBreach).filter(
        SecurityBreach.id == breach_id,
        SecurityBreach.organization_id == current_user.organization_id,
    ).first()

    if not breach:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Breach not found",
        )

    if breach.status == BreachStatus.RESOLVED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Breach is already resolved",
        )

    # Update breach record
    now = datetime.now(UTC)
    breach.status = BreachStatus.RESOLVED
    breach.resolved_at = now
    if breach.contained_at is None:
        breach.contained_at = now

    # Log the action
    log_action(
        db=db,
        user=current_user,
        organization_id=current_user.organization_id,
        action=AuditAction.BREACH_RESOLVED,
        request=request,
        entity_type=EntityType.SECURITY_BREACH,
        entity_id=breach_id,
        metadata={
            "breach_title": breach.title,
            "hours_to_resolution": str(
                round((now - breach.detected_at).total_seconds() / 3600, 1)
            ),
            "authority_notified": str(breach.authority_notified),
            "users_notified": str(breach.users_notified),
        },
    )

    db.commit()
    db.refresh(breach)

    return _serialize_breach(breach)

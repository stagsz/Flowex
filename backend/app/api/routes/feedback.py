"""Beta feedback API endpoints for collecting pilot customer feedback."""

from datetime import UTC, datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.core.deps import get_current_user, get_db
from app.core.rate_limiting import default_limit, limiter
from app.models import (
    BetaFeedback,
    Drawing,
    FeedbackPriority,
    FeedbackStatus,
    FeedbackType,
    User,
)

router = APIRouter(prefix="/feedback", tags=["feedback"])


# =============================================================================
# Request/Response Models
# =============================================================================


class FeedbackCreate(BaseModel):
    """Request model for creating feedback."""

    feedback_type: FeedbackType = FeedbackType.GENERAL
    priority: FeedbackPriority = FeedbackPriority.MEDIUM
    title: str = Field(..., min_length=3, max_length=200)
    description: str = Field(..., min_length=10, max_length=5000)
    drawing_id: UUID | None = None
    page_url: str | None = Field(None, max_length=500)
    user_agent: str | None = Field(None, max_length=500)
    screen_size: str | None = Field(None, max_length=50)
    satisfaction_rating: int | None = Field(None, ge=1, le=5)


class FeedbackResponse(BaseModel):
    """Response model for feedback items."""

    id: UUID
    user_id: UUID
    organization_id: UUID
    drawing_id: UUID | None
    feedback_type: FeedbackType
    priority: FeedbackPriority
    title: str
    description: str
    page_url: str | None
    user_agent: str | None
    screen_size: str | None
    satisfaction_rating: int | None
    status: FeedbackStatus
    resolution_notes: str | None
    resolved_at: datetime | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class FeedbackListResponse(BaseModel):
    """Response model for listing feedback items."""

    items: list[FeedbackResponse]
    total: int
    page: int
    page_size: int


class FeedbackStatusUpdate(BaseModel):
    """Request model for updating feedback status (admin only)."""

    status: FeedbackStatus
    resolution_notes: str | None = Field(None, max_length=2000)


class FeedbackStats(BaseModel):
    """Response model for feedback statistics."""

    total_feedback: int
    by_type: dict[str, int]
    by_status: dict[str, int]
    by_priority: dict[str, int]
    average_satisfaction: float | None
    recent_feedback_count: int


# =============================================================================
# API Endpoints
# =============================================================================


@router.post("", response_model=FeedbackResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit(default_limit)
async def create_feedback(
    request: Request,
    feedback_data: FeedbackCreate,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> FeedbackResponse:
    """Submit beta feedback.

    Allows authenticated users to submit feedback about their experience
    with the platform. Feedback can be associated with a specific drawing
    if relevant.
    """
    # Validate drawing_id if provided
    if feedback_data.drawing_id:
        drawing = db.query(Drawing).filter(Drawing.id == feedback_data.drawing_id).first()
        if not drawing:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Drawing not found",
            )

    # Create feedback
    feedback = BetaFeedback(
        user_id=current_user.id,
        organization_id=current_user.organization_id,
        drawing_id=feedback_data.drawing_id,
        feedback_type=feedback_data.feedback_type,
        priority=feedback_data.priority,
        title=feedback_data.title,
        description=feedback_data.description,
        page_url=feedback_data.page_url,
        user_agent=feedback_data.user_agent,
        screen_size=feedback_data.screen_size,
        satisfaction_rating=feedback_data.satisfaction_rating,
    )

    db.add(feedback)
    db.commit()
    db.refresh(feedback)

    return FeedbackResponse.model_validate(feedback)


@router.get("", response_model=FeedbackListResponse)
@limiter.limit(default_limit)
async def list_feedback(
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    feedback_type: FeedbackType | None = None,
    status: FeedbackStatus | None = None,
    priority: FeedbackPriority | None = None,
) -> FeedbackListResponse:
    """List feedback submitted by the current user or organization.

    Admins can see all feedback from their organization.
    Regular users can only see their own feedback.
    """
    # Build query
    query = db.query(BetaFeedback).filter(
        BetaFeedback.organization_id == current_user.organization_id
    )

    # Non-admins can only see their own feedback
    if current_user.role.value != "admin":
        query = query.filter(BetaFeedback.user_id == current_user.id)

    # Apply filters
    if feedback_type:
        query = query.filter(BetaFeedback.feedback_type == feedback_type)
    if status:
        query = query.filter(BetaFeedback.status == status)
    if priority:
        query = query.filter(BetaFeedback.priority == priority)

    # Get total count
    total = query.count()

    # Apply pagination and ordering
    items = (
        query.order_by(desc(BetaFeedback.created_at))
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    return FeedbackListResponse(
        items=[FeedbackResponse.model_validate(item) for item in items],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/stats", response_model=FeedbackStats)
@limiter.limit(default_limit)
async def get_feedback_stats(
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> FeedbackStats:
    """Get feedback statistics for the organization.

    Only accessible to admins.
    """
    if current_user.role.value != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )

    # Base query for organization
    base_query = db.query(BetaFeedback).filter(
        BetaFeedback.organization_id == current_user.organization_id
    )

    # Total feedback
    total_feedback = base_query.count()

    # By type
    by_type: dict[str, int] = {}
    for ft in FeedbackType:
        count = base_query.filter(BetaFeedback.feedback_type == ft).count()
        by_type[ft.value] = count

    # By status
    by_status: dict[str, int] = {}
    for fs in FeedbackStatus:
        count = base_query.filter(BetaFeedback.status == fs).count()
        by_status[fs.value] = count

    # By priority
    by_priority: dict[str, int] = {}
    for fp in FeedbackPriority:
        count = base_query.filter(BetaFeedback.priority == fp).count()
        by_priority[fp.value] = count

    # Average satisfaction
    ratings = base_query.filter(BetaFeedback.satisfaction_rating.isnot(None)).all()
    if ratings:
        avg_satisfaction = sum(r.satisfaction_rating for r in ratings if r.satisfaction_rating) / len(ratings)
    else:
        avg_satisfaction = None

    # Recent feedback (last 7 days)
    from datetime import timedelta

    seven_days_ago = datetime.now(UTC) - timedelta(days=7)
    recent_count = base_query.filter(BetaFeedback.created_at >= seven_days_ago).count()

    return FeedbackStats(
        total_feedback=total_feedback,
        by_type=by_type,
        by_status=by_status,
        by_priority=by_priority,
        average_satisfaction=avg_satisfaction,
        recent_feedback_count=recent_count,
    )


@router.get("/{feedback_id}", response_model=FeedbackResponse)
@limiter.limit(default_limit)
async def get_feedback(
    request: Request,
    feedback_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> FeedbackResponse:
    """Get a specific feedback item."""
    feedback = db.query(BetaFeedback).filter(BetaFeedback.id == feedback_id).first()

    if not feedback:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Feedback not found",
        )

    # Check access
    if feedback.organization_id != current_user.organization_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied",
        )

    # Non-admins can only see their own feedback
    if current_user.role.value != "admin" and feedback.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied",
        )

    return FeedbackResponse.model_validate(feedback)


@router.patch("/{feedback_id}/status", response_model=FeedbackResponse)
@limiter.limit(default_limit)
async def update_feedback_status(
    request: Request,
    feedback_id: UUID,
    status_update: FeedbackStatusUpdate,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> FeedbackResponse:
    """Update feedback status (admin only).

    Admins can acknowledge, mark in-progress, or resolve feedback items.
    """
    if current_user.role.value != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )

    feedback = db.query(BetaFeedback).filter(BetaFeedback.id == feedback_id).first()

    if not feedback:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Feedback not found",
        )

    if feedback.organization_id != current_user.organization_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied",
        )

    # Update status
    feedback.status = status_update.status
    if status_update.resolution_notes:
        feedback.resolution_notes = status_update.resolution_notes

    # Set resolved_at timestamp if status is resolved or wont_fix
    if status_update.status in (FeedbackStatus.RESOLVED, FeedbackStatus.WONT_FIX):
        feedback.resolved_at = datetime.now(UTC)
    else:
        feedback.resolved_at = None

    db.commit()
    db.refresh(feedback)

    return FeedbackResponse.model_validate(feedback)


@router.delete("/{feedback_id}", status_code=status.HTTP_204_NO_CONTENT)
@limiter.limit(default_limit)
async def delete_feedback(
    request: Request,
    feedback_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> None:
    """Delete a feedback item.

    Users can delete their own feedback.
    Admins can delete any feedback from their organization.
    """
    feedback = db.query(BetaFeedback).filter(BetaFeedback.id == feedback_id).first()

    if not feedback:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Feedback not found",
        )

    # Check access
    if feedback.organization_id != current_user.organization_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied",
        )

    # Non-admins can only delete their own feedback
    if current_user.role.value != "admin" and feedback.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied",
        )

    db.delete(feedback)
    db.commit()

"""Beta feedback model for collecting pilot customer feedback."""

import uuid
from datetime import datetime
from enum import Enum

from sqlalchemy import DateTime, Enum as SQLEnum, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin


class FeedbackType(str, Enum):
    """Type of feedback being submitted."""

    BUG = "bug"
    FEATURE_REQUEST = "feature_request"
    USABILITY = "usability"
    PERFORMANCE = "performance"
    GENERAL = "general"


class FeedbackPriority(str, Enum):
    """Priority/severity of the feedback."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class FeedbackStatus(str, Enum):
    """Status of the feedback item."""

    NEW = "new"
    ACKNOWLEDGED = "acknowledged"
    IN_PROGRESS = "in_progress"
    RESOLVED = "resolved"
    WONT_FIX = "wont_fix"


class BetaFeedback(Base, UUIDMixin, TimestampMixin):
    """Beta feedback submitted by pilot customers."""

    __tablename__ = "beta_feedback"

    # Foreign keys
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
    )
    drawing_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("drawings.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Feedback content
    feedback_type: Mapped[FeedbackType] = mapped_column(
        SQLEnum(FeedbackType),
        nullable=False,
        default=FeedbackType.GENERAL,
    )
    priority: Mapped[FeedbackPriority] = mapped_column(
        SQLEnum(FeedbackPriority),
        nullable=False,
        default=FeedbackPriority.MEDIUM,
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)

    # Context information
    page_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(String(500), nullable=True)
    screen_size: Mapped[str | None] = mapped_column(String(50), nullable=True)

    # User satisfaction (1-5 rating)
    satisfaction_rating: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Status tracking
    status: Mapped[FeedbackStatus] = mapped_column(
        SQLEnum(FeedbackStatus),
        nullable=False,
        default=FeedbackStatus.NEW,
    )
    resolution_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    resolved_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="beta_feedback")
    organization: Mapped["Organization"] = relationship(
        "Organization", back_populates="beta_feedback"
    )
    drawing: Mapped["Drawing"] = relationship("Drawing", back_populates="beta_feedback")


# Import at the end to avoid circular imports
from app.models.drawing import Drawing  # noqa: E402, F401
from app.models.organization import Organization  # noqa: E402, F401
from app.models.user import User  # noqa: E402, F401

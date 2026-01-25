"""Security breach model for GDPR Article 33 compliance (breach notification)."""

import uuid
from datetime import datetime
from enum import Enum

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin


class BreachSeverity(str, Enum):
    """Severity level of the security breach."""

    LOW = "low"  # Minor, no significant risk
    MEDIUM = "medium"  # Moderate risk, limited data exposure
    HIGH = "high"  # Significant risk, sensitive data potentially exposed
    CRITICAL = "critical"  # Severe risk, requires immediate notification


class BreachStatus(str, Enum):
    """Status of breach investigation and notification."""

    DETECTED = "detected"  # Breach detected, investigation starting
    INVESTIGATING = "investigating"  # Under active investigation
    CONTAINED = "contained"  # Breach contained, assessing impact
    NOTIFYING = "notifying"  # Notifying affected parties
    RESOLVED = "resolved"  # Incident closed


class BreachCategory(str, Enum):
    """Category/type of security breach per GDPR Article 4(12)."""

    CONFIDENTIALITY = "confidentiality"  # Unauthorized disclosure or access
    INTEGRITY = "integrity"  # Unauthorized alteration of data
    AVAILABILITY = "availability"  # Loss of access to data


class SecurityBreach(Base, UUIDMixin, TimestampMixin):
    """Security breach record for GDPR Article 33 compliance.

    GDPR Article 33 requires:
    - Notification to supervisory authority within 72 hours
    - Documentation of all breaches (even if not notified)
    - Notification to affected data subjects if high risk (Article 34)

    This model tracks:
    - Breach details and timeline
    - Investigation status
    - Notification status (authority and users)
    - Affected data categories and user counts
    """

    __tablename__ = "security_breaches"

    # Foreign keys
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    reported_by_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,  # Null if system-detected or reporter deleted
    )

    # Breach identification
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    severity: Mapped[BreachSeverity] = mapped_column(
        SQLEnum(BreachSeverity),
        nullable=False,
        default=BreachSeverity.MEDIUM,
        index=True,
    )
    status: Mapped[BreachStatus] = mapped_column(
        SQLEnum(BreachStatus),
        nullable=False,
        default=BreachStatus.DETECTED,
        index=True,
    )
    category: Mapped[BreachCategory] = mapped_column(
        SQLEnum(BreachCategory),
        nullable=False,
        default=BreachCategory.CONFIDENTIALITY,
    )

    # Timeline (GDPR Article 33 requires 72-hour notification)
    detected_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    contained_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    resolved_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Impact assessment
    affected_users_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )
    data_categories_affected: Mapped[list[str] | None] = mapped_column(
        JSON,
        nullable=True,
    )  # e.g., ["email", "name", "drawings"]

    # Notification tracking
    authority_notified: Mapped[bool] = mapped_column(
        nullable=False,
        default=False,
    )
    authority_notified_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    authority_reference: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )  # Reference number from supervisory authority

    users_notified: Mapped[bool] = mapped_column(
        nullable=False,
        default=False,
    )
    users_notified_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Investigation details
    root_cause: Mapped[str | None] = mapped_column(Text, nullable=True)
    remediation_steps: Mapped[str | None] = mapped_column(Text, nullable=True)
    preventive_measures: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Additional context
    extra_data: Mapped[dict[str, str] | None] = mapped_column(JSON, nullable=True)

    # Relationships
    organization: Mapped["Organization"] = relationship(
        "Organization", back_populates="security_breaches"
    )
    reported_by: Mapped["User | None"] = relationship(
        "User", back_populates="reported_breaches"
    )


# Import at the end to avoid circular imports
from app.models.organization import Organization  # noqa: E402, F401
from app.models.user import User  # noqa: E402, F401

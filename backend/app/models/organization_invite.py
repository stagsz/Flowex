import enum
import secrets
import uuid
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Enum, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin
from app.models.user import UserRole

if TYPE_CHECKING:
    from app.models.organization import Organization
    from app.models.user import User


class InviteStatus(str, enum.Enum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    EXPIRED = "expired"
    REVOKED = "revoked"


def generate_invite_token() -> str:
    """Generate a secure random invite token."""
    return secrets.token_urlsafe(32)


def default_expires_at() -> datetime:
    """Default expiration: 7 days from now."""
    return datetime.now(UTC) + timedelta(days=7)


class OrganizationInvite(Base, UUIDMixin, TimestampMixin):
    """Pending invitations to join an organization."""

    __tablename__ = "organization_invites"

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    email: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    role: Mapped[UserRole] = mapped_column(
        Enum(UserRole, values_callable=lambda x: [e.value for e in x]),
        default=UserRole.MEMBER,
        nullable=False,
    )
    token: Mapped[str] = mapped_column(
        String(64), unique=True, nullable=False, index=True, default=generate_invite_token
    )
    status: Mapped[InviteStatus] = mapped_column(
        Enum(InviteStatus, values_callable=lambda x: [e.value for e in x]),
        default=InviteStatus.PENDING,
        nullable=False,
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=default_expires_at,
    )
    invited_by_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    accepted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Relationships
    organization: Mapped["Organization"] = relationship(
        "Organization", back_populates="invites"
    )
    invited_by: Mapped["User | None"] = relationship("User", foreign_keys=[invited_by_id])

    @property
    def is_expired(self) -> bool:
        """Check if the invitation has expired."""
        return datetime.now(UTC) > self.expires_at

    @property
    def is_valid(self) -> bool:
        """Check if the invitation is still valid (pending and not expired)."""
        return self.status == InviteStatus.PENDING and not self.is_expired

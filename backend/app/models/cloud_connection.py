import enum
import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Enum, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.models.organization import Organization
    from app.models.user import User


class CloudProvider(str, enum.Enum):
    """Supported cloud storage providers."""

    ONEDRIVE = "onedrive"
    SHAREPOINT = "sharepoint"
    GOOGLE_DRIVE = "google_drive"


class CloudConnection(Base, UUIDMixin, TimestampMixin):
    """Cloud storage connection for importing/exporting files."""

    __tablename__ = "cloud_connections"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    provider: Mapped[CloudProvider] = mapped_column(
        Enum(CloudProvider),
        nullable=False,
    )
    account_email: Mapped[str] = mapped_column(String(255), nullable=False)
    account_name: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Encrypted tokens (using Fernet encryption)
    access_token_encrypted: Mapped[str] = mapped_column(Text, nullable=False)
    refresh_token_encrypted: Mapped[str] = mapped_column(Text, nullable=False)
    token_expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    # SharePoint-specific fields
    site_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    site_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    drive_id: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Usage tracking
    last_used_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Relationships
    user: Mapped["User"] = relationship("User", backref="cloud_connections")
    organization: Mapped["Organization"] = relationship(
        "Organization", backref="cloud_connections"
    )

"""Audit log model for tracking user activity (SEC-04 compliance)."""

import uuid
from datetime import datetime
from enum import Enum

from sqlalchemy import DateTime, ForeignKey, Index, String
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, UUIDMixin


class AuditAction(str, Enum):
    """Audit action types for tracking user activity."""

    # Authentication
    LOGIN = "login"
    LOGOUT = "logout"
    TOKEN_REFRESH = "token_refresh"

    # User management
    USER_INVITE = "user_invite"
    USER_ROLE_UPDATE = "user_role_update"
    USER_REMOVE = "user_remove"
    INVITE_REVOKE = "invite_revoke"
    INVITE_ACCEPT = "invite_accept"

    # Project operations
    PROJECT_CREATE = "project_create"
    PROJECT_UPDATE = "project_update"
    PROJECT_DELETE = "project_delete"

    # Drawing operations
    DRAWING_UPLOAD = "drawing_upload"
    DRAWING_PROCESS = "drawing_process"
    DRAWING_DELETE = "drawing_delete"

    # Symbol operations
    SYMBOL_CREATE = "symbol_create"
    SYMBOL_UPDATE = "symbol_update"
    SYMBOL_DELETE = "symbol_delete"
    SYMBOL_VERIFY = "symbol_verify"
    SYMBOL_BULK_VERIFY = "symbol_bulk_verify"
    SYMBOL_FLAG = "symbol_flag"

    # Line operations
    LINE_CREATE = "line_create"
    LINE_UPDATE = "line_update"
    LINE_DELETE = "line_delete"
    LINE_VERIFY = "line_verify"
    LINE_BULK_VERIFY = "line_bulk_verify"

    # Export operations
    EXPORT_DXF = "export_dxf"
    EXPORT_LIST = "export_list"
    EXPORT_REPORT = "export_report"
    EXPORT_CHECKLIST = "export_checklist"

    # Cloud storage operations
    CLOUD_CONNECT = "cloud_connect"
    CLOUD_DISCONNECT = "cloud_disconnect"
    CLOUD_IMPORT = "cloud_import"
    CLOUD_EXPORT = "cloud_export"

    # GDPR operations
    DATA_EXPORT_REQUEST = "data_export_request"
    ACCOUNT_DELETION_REQUEST = "account_deletion_request"


class EntityType(str, Enum):
    """Entity types for audit log entries."""

    USER = "user"
    ORGANIZATION = "organization"
    PROJECT = "project"
    DRAWING = "drawing"
    SYMBOL = "symbol"
    LINE = "line"
    TEXT_ANNOTATION = "text_annotation"
    CLOUD_CONNECTION = "cloud_connection"
    INVITE = "invite"
    EXPORT_JOB = "export_job"


class AuditLog(Base, UUIDMixin):
    """Audit log entry for user activity tracking.

    Implements SEC-04: User activity audit logging.
    Retention: 3 years per GDPR compliance (see spec).
    """

    __tablename__ = "audit_logs"

    # Foreign keys
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,  # Null if user deleted
        index=True,
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Action details
    action: Mapped[AuditAction] = mapped_column(
        SQLEnum(AuditAction),
        nullable=False,
        index=True,
    )
    entity_type: Mapped[EntityType | None] = mapped_column(
        SQLEnum(EntityType),
        nullable=True,
    )
    entity_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        nullable=True,
    )

    # Request context
    ip_address: Mapped[str | None] = mapped_column(String(45), nullable=True)  # IPv6 max length
    user_agent: Mapped[str | None] = mapped_column(String(500), nullable=True)

    # Additional context (JSON for flexibility)
    extra_data: Mapped[dict[str, str] | None] = mapped_column(JSON, nullable=True)

    # Timestamp
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
    )

    # Relationships
    user: Mapped["User | None"] = relationship("User", back_populates="audit_logs")
    organization: Mapped["Organization"] = relationship(
        "Organization", back_populates="audit_logs"
    )

    # Composite indexes for common queries
    __table_args__ = (
        Index("ix_audit_logs_org_timestamp", "organization_id", "timestamp"),
        Index("ix_audit_logs_user_timestamp", "user_id", "timestamp"),
        Index("ix_audit_logs_org_action", "organization_id", "action"),
    )


# Import at the end to avoid circular imports
from app.models.organization import Organization  # noqa: E402, F401
from app.models.user import User  # noqa: E402, F401

"""Add audit_logs table for user activity tracking (SEC-04)

Revision ID: 005
Revises: 004
Create Date: 2026-01-21

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "005"
down_revision: Union[str, None] = "004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create audit action enum
    audit_action_enum = postgresql.ENUM(
        "login",
        "logout",
        "token_refresh",
        "user_invite",
        "user_role_update",
        "user_remove",
        "invite_revoke",
        "invite_accept",
        "project_create",
        "project_update",
        "project_delete",
        "drawing_upload",
        "drawing_process",
        "drawing_delete",
        "symbol_create",
        "symbol_update",
        "symbol_delete",
        "symbol_verify",
        "symbol_bulk_verify",
        "symbol_flag",
        "line_create",
        "line_update",
        "line_delete",
        "line_verify",
        "line_bulk_verify",
        "export_dxf",
        "export_list",
        "export_report",
        "export_checklist",
        "cloud_connect",
        "cloud_disconnect",
        "cloud_import",
        "cloud_export",
        "data_export_request",
        "account_deletion_request",
        name="auditaction",
        create_type=False,
    )
    audit_action_enum.create(op.get_bind(), checkfirst=True)

    # Create entity type enum
    entity_type_enum = postgresql.ENUM(
        "user",
        "organization",
        "project",
        "drawing",
        "symbol",
        "line",
        "text_annotation",
        "cloud_connection",
        "invite",
        "export_job",
        name="entitytype",
        create_type=False,
    )
    entity_type_enum.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "audit_logs",
        sa.Column(
            "id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False
        ),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "organization_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("organizations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "action",
            audit_action_enum,
            nullable=False,
        ),
        sa.Column(
            "entity_type",
            entity_type_enum,
            nullable=True,
        ),
        sa.Column(
            "entity_id",
            postgresql.UUID(as_uuid=True),
            nullable=True,
        ),
        sa.Column("ip_address", sa.String(45), nullable=True),
        sa.Column("user_agent", sa.String(500), nullable=True),
        sa.Column("extra_data", postgresql.JSON, nullable=True),
        sa.Column(
            "timestamp",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
    )

    # Create indexes for common queries
    op.create_index(
        "ix_audit_logs_user_id",
        "audit_logs",
        ["user_id"],
        unique=False,
    )
    op.create_index(
        "ix_audit_logs_organization_id",
        "audit_logs",
        ["organization_id"],
        unique=False,
    )
    op.create_index(
        "ix_audit_logs_action",
        "audit_logs",
        ["action"],
        unique=False,
    )
    op.create_index(
        "ix_audit_logs_timestamp",
        "audit_logs",
        ["timestamp"],
        unique=False,
    )
    # Composite indexes for common queries
    op.create_index(
        "ix_audit_logs_org_timestamp",
        "audit_logs",
        ["organization_id", "timestamp"],
        unique=False,
    )
    op.create_index(
        "ix_audit_logs_user_timestamp",
        "audit_logs",
        ["user_id", "timestamp"],
        unique=False,
    )
    op.create_index(
        "ix_audit_logs_org_action",
        "audit_logs",
        ["organization_id", "action"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_audit_logs_org_action", table_name="audit_logs")
    op.drop_index("ix_audit_logs_user_timestamp", table_name="audit_logs")
    op.drop_index("ix_audit_logs_org_timestamp", table_name="audit_logs")
    op.drop_index("ix_audit_logs_timestamp", table_name="audit_logs")
    op.drop_index("ix_audit_logs_action", table_name="audit_logs")
    op.drop_index("ix_audit_logs_organization_id", table_name="audit_logs")
    op.drop_index("ix_audit_logs_user_id", table_name="audit_logs")
    op.drop_table("audit_logs")

    # Drop enum types
    op.execute("DROP TYPE IF EXISTS entitytype")
    op.execute("DROP TYPE IF EXISTS auditaction")

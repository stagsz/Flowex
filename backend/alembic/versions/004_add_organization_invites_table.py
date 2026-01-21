"""Add organization_invites table for user invitations

Revision ID: 004
Revises: 003
Create Date: 2026-01-21

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "004"
down_revision: Union[str, None] = "003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create invite status enum
    invite_status_enum = postgresql.ENUM(
        "pending",
        "accepted",
        "expired",
        "revoked",
        name="invitestatus",
        create_type=False,
    )
    invite_status_enum.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "organization_invites",
        sa.Column(
            "id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False
        ),
        sa.Column(
            "organization_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("organizations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column(
            "role",
            postgresql.ENUM("admin", "member", "viewer", name="userrole", create_type=False),
            nullable=False,
            server_default="member",
        ),
        sa.Column("token", sa.String(64), unique=True, nullable=False),
        sa.Column(
            "status",
            invite_status_enum,
            nullable=False,
            server_default="pending",
        ),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "invited_by_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("accepted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            onupdate=sa.func.now(),
            nullable=False,
        ),
    )

    # Create indexes for common queries
    op.create_index(
        "ix_organization_invites_organization_id",
        "organization_invites",
        ["organization_id"],
        unique=False,
    )
    op.create_index(
        "ix_organization_invites_email",
        "organization_invites",
        ["email"],
        unique=False,
    )
    op.create_index(
        "ix_organization_invites_token",
        "organization_invites",
        ["token"],
        unique=True,
    )
    op.create_index(
        "ix_organization_invites_status",
        "organization_invites",
        ["status"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_organization_invites_status", table_name="organization_invites")
    op.drop_index("ix_organization_invites_token", table_name="organization_invites")
    op.drop_index("ix_organization_invites_email", table_name="organization_invites")
    op.drop_index(
        "ix_organization_invites_organization_id", table_name="organization_invites"
    )
    op.drop_table("organization_invites")

    # Drop enum type
    op.execute("DROP TYPE IF EXISTS invitestatus")

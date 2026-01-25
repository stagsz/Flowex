"""Add data retention fields for GDPR-08 compliance

Adds:
- drawings.last_accessed_at: Tracks when a drawing was last accessed
- users.scheduled_deletion_at: Scheduled account deletion timestamp
- users.deletion_reason: Optional reason for account deletion

Revision ID: 006
Revises: 005
Create Date: 2026-01-25

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "006"
down_revision: Union[str, None] = "005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add last_accessed_at to drawings table for retention tracking
    op.add_column(
        "drawings",
        sa.Column("last_accessed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(
        "ix_drawings_last_accessed_at",
        "drawings",
        ["last_accessed_at"],
        unique=False,
    )

    # Add scheduled_deletion_at to users table for deletion grace period
    op.add_column(
        "users",
        sa.Column("scheduled_deletion_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(
        "ix_users_scheduled_deletion_at",
        "users",
        ["scheduled_deletion_at"],
        unique=False,
    )

    # Add deletion_reason to users table
    op.add_column(
        "users",
        sa.Column("deletion_reason", sa.String(500), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("users", "deletion_reason")
    op.drop_index("ix_users_scheduled_deletion_at", table_name="users")
    op.drop_column("users", "scheduled_deletion_at")
    op.drop_index("ix_drawings_last_accessed_at", table_name="drawings")
    op.drop_column("drawings", "last_accessed_at")

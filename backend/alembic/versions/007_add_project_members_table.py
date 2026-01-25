"""Add project_members table for project-level permissions (PM-05)

Enables per-project access control with owner/editor/viewer roles,
independent of organization-level membership.

Revision ID: 007
Revises: 006
Create Date: 2026-01-25

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "007"
down_revision: Union[str, None] = "006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create project_members table
    op.create_table(
        "project_members",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "role",
            sa.Enum("owner", "editor", "viewer", name="projectrole"),
            nullable=False,
            server_default="editor",
        ),
        sa.Column("added_by_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(
            ["project_id"], ["projects.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["added_by_id"], ["users.id"], ondelete="SET NULL"
        ),
        sa.UniqueConstraint("project_id", "user_id", name="uq_project_member"),
    )

    # Create indexes for efficient lookups
    op.create_index(
        "ix_project_members_project_id",
        "project_members",
        ["project_id"],
        unique=False,
    )
    op.create_index(
        "ix_project_members_user_id",
        "project_members",
        ["user_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_project_members_user_id", table_name="project_members")
    op.drop_index("ix_project_members_project_id", table_name="project_members")
    op.drop_table("project_members")
    # Drop the enum type
    op.execute("DROP TYPE IF EXISTS projectrole")

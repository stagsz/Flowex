"""Add beta_feedback table for pilot customer feedback

Revision ID: 003
Revises: 002
Create Date: 2026-01-21

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "003"
down_revision: Union[str, None] = "002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create enum types
    feedback_type_enum = postgresql.ENUM(
        "bug",
        "feature_request",
        "usability",
        "performance",
        "general",
        name="feedbacktype",
        create_type=False,
    )
    feedback_priority_enum = postgresql.ENUM(
        "low",
        "medium",
        "high",
        "critical",
        name="feedbackpriority",
        create_type=False,
    )
    feedback_status_enum = postgresql.ENUM(
        "new",
        "acknowledged",
        "in_progress",
        "resolved",
        "wont_fix",
        name="feedbackstatus",
        create_type=False,
    )

    # Create the enums in the database
    feedback_type_enum.create(op.get_bind(), checkfirst=True)
    feedback_priority_enum.create(op.get_bind(), checkfirst=True)
    feedback_status_enum.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "beta_feedback",
        sa.Column(
            "id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False
        ),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "organization_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("organizations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "drawing_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("drawings.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "feedback_type",
            feedback_type_enum,
            nullable=False,
            server_default="general",
        ),
        sa.Column(
            "priority",
            feedback_priority_enum,
            nullable=False,
            server_default="medium",
        ),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("description", sa.Text, nullable=False),
        sa.Column("page_url", sa.String(500), nullable=True),
        sa.Column("user_agent", sa.String(500), nullable=True),
        sa.Column("screen_size", sa.String(50), nullable=True),
        sa.Column("satisfaction_rating", sa.Integer, nullable=True),
        sa.Column(
            "status",
            feedback_status_enum,
            nullable=False,
            server_default="new",
        ),
        sa.Column("resolution_notes", sa.Text, nullable=True),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
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
        "ix_beta_feedback_user_id", "beta_feedback", ["user_id"], unique=False
    )
    op.create_index(
        "ix_beta_feedback_organization_id",
        "beta_feedback",
        ["organization_id"],
        unique=False,
    )
    op.create_index(
        "ix_beta_feedback_status", "beta_feedback", ["status"], unique=False
    )
    op.create_index(
        "ix_beta_feedback_created_at", "beta_feedback", ["created_at"], unique=False
    )


def downgrade() -> None:
    op.drop_index("ix_beta_feedback_created_at", table_name="beta_feedback")
    op.drop_index("ix_beta_feedback_status", table_name="beta_feedback")
    op.drop_index("ix_beta_feedback_organization_id", table_name="beta_feedback")
    op.drop_index("ix_beta_feedback_user_id", table_name="beta_feedback")
    op.drop_table("beta_feedback")

    # Drop enum types
    op.execute("DROP TYPE IF EXISTS feedbackstatus")
    op.execute("DROP TYPE IF EXISTS feedbackpriority")
    op.execute("DROP TYPE IF EXISTS feedbacktype")

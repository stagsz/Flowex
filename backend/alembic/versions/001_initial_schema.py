"""Initial schema

Revision ID: 001
Revises:
Create Date: 2026-01-19

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Organizations table
    op.create_table(
        "organizations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("slug", sa.String(100), unique=True, nullable=False, index=True),
        sa.Column(
            "subscription_tier",
            sa.Enum("free_trial", "starter", "professional", "business", name="subscriptiontier"),
            nullable=False,
            server_default="free_trial",
        ),
        sa.Column("monthly_pid_limit", sa.Integer(), nullable=False, server_default="5"),
        sa.Column("pids_used_this_month", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )

    # Users table
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "organization_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("organizations.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("email", sa.String(255), unique=True, nullable=False, index=True),
        sa.Column("name", sa.String(255), nullable=True),
        sa.Column(
            "role",
            sa.Enum("admin", "member", "viewer", name="userrole"),
            nullable=False,
            server_default="member",
        ),
        sa.Column(
            "sso_provider", sa.Enum("microsoft", "google", name="ssoprovider"), nullable=True
        ),
        sa.Column("sso_subject_id", sa.String(255), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )

    # Projects table
    op.create_table(
        "projects",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "organization_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("organizations.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("is_archived", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )

    # Drawings table
    op.create_table(
        "drawings",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "project_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("projects.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("original_filename", sa.String(255), nullable=False),
        sa.Column("storage_path", sa.String(512), nullable=False),
        sa.Column("file_size_bytes", sa.Integer(), nullable=False),
        sa.Column(
            "file_type", sa.Enum("pdf_vector", "pdf_scanned", name="filetype"), nullable=True
        ),
        sa.Column(
            "status",
            sa.Enum("uploaded", "processing", "review", "complete", "error", name="drawingstatus"),
            nullable=False,
            server_default="uploaded",
            index=True,
        ),
        sa.Column("error_message", sa.String(1000), nullable=True),
        sa.Column("processing_started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("processing_completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )

    # Symbols table
    op.create_table(
        "symbols",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "drawing_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("drawings.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("symbol_class", sa.String(100), nullable=False, index=True),
        sa.Column(
            "category",
            sa.Enum("equipment", "instrument", "valve", "other", name="symbolcategory"),
            nullable=False,
            server_default="other",
        ),
        sa.Column("tag_number", sa.String(100), nullable=True, index=True),
        sa.Column("bbox_x", sa.Float(), nullable=False),
        sa.Column("bbox_y", sa.Float(), nullable=False),
        sa.Column("bbox_width", sa.Float(), nullable=False),
        sa.Column("bbox_height", sa.Float(), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=True),
        sa.Column("is_verified", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )

    # Lines table
    op.create_table(
        "lines",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "drawing_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("drawings.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("line_number", sa.String(100), nullable=True, index=True),
        sa.Column("start_x", sa.Float(), nullable=False),
        sa.Column("start_y", sa.Float(), nullable=False),
        sa.Column("end_x", sa.Float(), nullable=False),
        sa.Column("end_y", sa.Float(), nullable=False),
        sa.Column("line_spec", sa.String(100), nullable=True),
        sa.Column("pipe_class", sa.String(50), nullable=True),
        sa.Column("insulation", sa.String(50), nullable=True),
        sa.Column("confidence", sa.Float(), nullable=True),
        sa.Column("is_verified", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )

    # Text annotations table
    op.create_table(
        "text_annotations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "drawing_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("drawings.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("text_content", sa.String(500), nullable=False),
        sa.Column("bbox_x", sa.Float(), nullable=False),
        sa.Column("bbox_y", sa.Float(), nullable=False),
        sa.Column("bbox_width", sa.Float(), nullable=False),
        sa.Column("bbox_height", sa.Float(), nullable=False),
        sa.Column("rotation", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("confidence", sa.Float(), nullable=True),
        sa.Column("is_verified", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column(
            "associated_symbol_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("symbols.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )


def downgrade() -> None:
    op.drop_table("text_annotations")
    op.drop_table("lines")
    op.drop_table("symbols")
    op.drop_table("drawings")
    op.drop_table("projects")
    op.drop_table("users")
    op.drop_table("organizations")

    # Drop enums
    op.execute("DROP TYPE IF EXISTS symbolcategory")
    op.execute("DROP TYPE IF EXISTS drawingstatus")
    op.execute("DROP TYPE IF EXISTS filetype")
    op.execute("DROP TYPE IF EXISTS ssoprovider")
    op.execute("DROP TYPE IF EXISTS userrole")
    op.execute("DROP TYPE IF EXISTS subscriptiontier")

"""Add security_breaches table for GDPR Article 33 compliance (breach notification)

GDPR Article 33 requires organizations to:
- Notify supervisory authority within 72 hours of breach detection
- Document all breaches (even if not notified)
- Notify affected users if high risk (Article 34)

This table tracks breach incidents, investigation status, and notification history.

Revision ID: 008
Revises: 007
Create Date: 2026-01-25

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "008"
down_revision: Union[str, None] = "007"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create enum types
    op.execute(
        "CREATE TYPE breachseverity AS ENUM ('low', 'medium', 'high', 'critical')"
    )
    op.execute(
        "CREATE TYPE breachstatus AS ENUM ('detected', 'investigating', 'contained', 'notifying', 'resolved')"
    )
    op.execute(
        "CREATE TYPE breachcategory AS ENUM ('confidentiality', 'integrity', 'availability')"
    )

    # Create security_breaches table
    op.create_table(
        "security_breaches",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("reported_by_id", postgresql.UUID(as_uuid=True), nullable=True),
        # Breach identification
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column(
            "severity",
            postgresql.ENUM(
                "low", "medium", "high", "critical",
                name="breachseverity",
                create_type=False,
            ),
            nullable=False,
            server_default="medium",
        ),
        sa.Column(
            "status",
            postgresql.ENUM(
                "detected", "investigating", "contained", "notifying", "resolved",
                name="breachstatus",
                create_type=False,
            ),
            nullable=False,
            server_default="detected",
        ),
        sa.Column(
            "category",
            postgresql.ENUM(
                "confidentiality", "integrity", "availability",
                name="breachcategory",
                create_type=False,
            ),
            nullable=False,
            server_default="confidentiality",
        ),
        # Timeline
        sa.Column("detected_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("contained_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        # Impact assessment
        sa.Column("affected_users_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("data_categories_affected", postgresql.JSON(), nullable=True),
        # Notification tracking
        sa.Column("authority_notified", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("authority_notified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("authority_reference", sa.String(100), nullable=True),
        sa.Column("users_notified", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("users_notified_at", sa.DateTime(timezone=True), nullable=True),
        # Investigation details
        sa.Column("root_cause", sa.Text(), nullable=True),
        sa.Column("remediation_steps", sa.Text(), nullable=True),
        sa.Column("preventive_measures", sa.Text(), nullable=True),
        # Additional context
        sa.Column("extra_data", postgresql.JSON(), nullable=True),
        # Timestamps
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
        # Constraints
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(
            ["organization_id"], ["organizations.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["reported_by_id"], ["users.id"], ondelete="SET NULL"
        ),
    )

    # Create indexes for efficient queries
    op.create_index(
        "ix_security_breaches_organization_id",
        "security_breaches",
        ["organization_id"],
        unique=False,
    )
    op.create_index(
        "ix_security_breaches_severity",
        "security_breaches",
        ["severity"],
        unique=False,
    )
    op.create_index(
        "ix_security_breaches_status",
        "security_breaches",
        ["status"],
        unique=False,
    )
    op.create_index(
        "ix_security_breaches_detected_at",
        "security_breaches",
        ["detected_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_security_breaches_detected_at", table_name="security_breaches")
    op.drop_index("ix_security_breaches_status", table_name="security_breaches")
    op.drop_index("ix_security_breaches_severity", table_name="security_breaches")
    op.drop_index("ix_security_breaches_organization_id", table_name="security_breaches")
    op.drop_table("security_breaches")
    # Drop enum types
    op.execute("DROP TYPE IF EXISTS breachcategory")
    op.execute("DROP TYPE IF EXISTS breachstatus")
    op.execute("DROP TYPE IF EXISTS breachseverity")

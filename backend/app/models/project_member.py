"""Project membership model for project-level permissions (PM-05)."""

import enum
import uuid
from typing import TYPE_CHECKING

from sqlalchemy import Enum, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.models.project import Project
    from app.models.user import User


class ProjectRole(str, enum.Enum):
    """Roles for project-level access control."""

    OWNER = "owner"  # Full control: can manage members, delete project
    EDITOR = "editor"  # Can edit drawings, symbols, exports
    VIEWER = "viewer"  # Read-only access to project and drawings


class ProjectMember(Base, UUIDMixin, TimestampMixin):
    """
    Membership linking users to projects with specific roles.

    This enables project-level permissions (PM-05) allowing:
    - Project owners to invite specific users to their projects
    - Different permission levels (owner/editor/viewer) per project
    - Access control independent of organization membership
    """

    __tablename__ = "project_members"

    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    role: Mapped[ProjectRole] = mapped_column(
        Enum(ProjectRole, values_callable=lambda x: [e.value for e in x]),
        default=ProjectRole.EDITOR,
        nullable=False,
    )
    added_by_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Unique constraint: one membership per user per project
    __table_args__ = (
        UniqueConstraint("project_id", "user_id", name="uq_project_member"),
    )

    # Relationships
    project: Mapped["Project"] = relationship("Project", back_populates="members")
    user: Mapped["User"] = relationship(
        "User", foreign_keys=[user_id], back_populates="project_memberships"
    )
    added_by: Mapped["User | None"] = relationship("User", foreign_keys=[added_by_id])

    def can_edit(self) -> bool:
        """Check if this member can edit project content."""
        return self.role in (ProjectRole.OWNER, ProjectRole.EDITOR)

    def can_manage_members(self) -> bool:
        """Check if this member can manage other project members."""
        return self.role == ProjectRole.OWNER

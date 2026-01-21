import enum
from typing import TYPE_CHECKING

from sqlalchemy import Enum, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.models.beta_feedback import BetaFeedback
    from app.models.project import Project
    from app.models.user import User


class SubscriptionTier(str, enum.Enum):
    FREE_TRIAL = "free_trial"
    STARTER = "starter"
    PROFESSIONAL = "professional"
    BUSINESS = "business"


class Organization(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "organizations"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    subscription_tier: Mapped[SubscriptionTier] = mapped_column(
        Enum(SubscriptionTier, values_callable=lambda x: [e.value for e in x]),
        default=SubscriptionTier.FREE_TRIAL,
        nullable=False,
    )
    monthly_pid_limit: Mapped[int] = mapped_column(Integer, default=5, nullable=False)
    pids_used_this_month: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Relationships
    users: Mapped[list["User"]] = relationship("User", back_populates="organization")
    projects: Mapped[list["Project"]] = relationship("Project", back_populates="organization")
    beta_feedback: Mapped[list["BetaFeedback"]] = relationship(
        "BetaFeedback", back_populates="organization", cascade="all, delete-orphan"
    )

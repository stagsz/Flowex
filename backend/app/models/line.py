import uuid
from typing import TYPE_CHECKING

from sqlalchemy import Float, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.models.drawing import Drawing


class Line(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "lines"

    drawing_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("drawings.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    line_number: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)

    # Line coordinates (start and end points)
    start_x: Mapped[float] = mapped_column(Float, nullable=False)
    start_y: Mapped[float] = mapped_column(Float, nullable=False)
    end_x: Mapped[float] = mapped_column(Float, nullable=False)
    end_y: Mapped[float] = mapped_column(Float, nullable=False)

    # Line properties
    line_spec: Mapped[str | None] = mapped_column(String(100), nullable=True)  # e.g., "6"-P-101-A1"
    pipe_class: Mapped[str | None] = mapped_column(String(50), nullable=True)
    insulation: Mapped[str | None] = mapped_column(String(50), nullable=True)

    # AI confidence and verification
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    is_verified: Mapped[bool] = mapped_column(default=False, nullable=False)
    is_deleted: Mapped[bool] = mapped_column(default=False, nullable=False)

    # Relationships
    drawing: Mapped["Drawing"] = relationship("Drawing", back_populates="lines")

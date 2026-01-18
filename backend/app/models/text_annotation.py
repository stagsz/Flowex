import uuid
from typing import TYPE_CHECKING

from sqlalchemy import Float, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.models.drawing import Drawing


class TextAnnotation(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "text_annotations"

    drawing_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("drawings.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    text_content: Mapped[str] = mapped_column(String(500), nullable=False)

    # Position and dimensions
    bbox_x: Mapped[float] = mapped_column(Float, nullable=False)
    bbox_y: Mapped[float] = mapped_column(Float, nullable=False)
    bbox_width: Mapped[float] = mapped_column(Float, nullable=False)
    bbox_height: Mapped[float] = mapped_column(Float, nullable=False)

    # Rotation in degrees (0, 90, 180, 270)
    rotation: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # AI confidence and verification
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    is_verified: Mapped[bool] = mapped_column(default=False, nullable=False)
    is_deleted: Mapped[bool] = mapped_column(default=False, nullable=False)

    # Associated symbol ID (if this text is a tag for a symbol)
    associated_symbol_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("symbols.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Relationships
    drawing: Mapped["Drawing"] = relationship("Drawing", back_populates="text_annotations")

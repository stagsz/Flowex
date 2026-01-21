import enum
import uuid
from typing import TYPE_CHECKING

from sqlalchemy import Enum, Float, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.models.drawing import Drawing


class SymbolCategory(str, enum.Enum):
    EQUIPMENT = "equipment"
    INSTRUMENT = "instrument"
    VALVE = "valve"
    OTHER = "other"


class Symbol(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "symbols"

    drawing_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("drawings.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    symbol_class: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    category: Mapped[SymbolCategory] = mapped_column(
        Enum(SymbolCategory, values_callable=lambda x: [e.value for e in x]),
        default=SymbolCategory.OTHER,
        nullable=False,
    )
    tag_number: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)

    # Bounding box coordinates (normalized 0-1 or pixel values)
    bbox_x: Mapped[float] = mapped_column(Float, nullable=False)
    bbox_y: Mapped[float] = mapped_column(Float, nullable=False)
    bbox_width: Mapped[float] = mapped_column(Float, nullable=False)
    bbox_height: Mapped[float] = mapped_column(Float, nullable=False)

    # AI confidence and verification
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    is_verified: Mapped[bool] = mapped_column(default=False, nullable=False)
    is_flagged: Mapped[bool] = mapped_column(default=False, nullable=False)
    is_deleted: Mapped[bool] = mapped_column(default=False, nullable=False)

    # Relationships
    drawing: Mapped["Drawing"] = relationship("Drawing", back_populates="symbols")

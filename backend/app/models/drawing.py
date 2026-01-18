import enum
import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.models.line import Line
    from app.models.project import Project
    from app.models.symbol import Symbol
    from app.models.text_annotation import TextAnnotation


class FileType(str, enum.Enum):
    PDF_VECTOR = "pdf_vector"
    PDF_SCANNED = "pdf_scanned"


class DrawingStatus(str, enum.Enum):
    UPLOADED = "uploaded"
    PROCESSING = "processing"
    REVIEW = "review"
    COMPLETE = "complete"
    ERROR = "error"


class Drawing(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "drawings"

    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    storage_path: Mapped[str] = mapped_column(String(512), nullable=False)
    file_size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    file_type: Mapped[FileType | None] = mapped_column(Enum(FileType), nullable=True)
    status: Mapped[DrawingStatus] = mapped_column(
        Enum(DrawingStatus),
        default=DrawingStatus.UPLOADED,
        nullable=False,
        index=True,
    )
    error_message: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    processing_started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    processing_completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Relationships
    project: Mapped["Project"] = relationship("Project", back_populates="drawings")
    symbols: Mapped[list["Symbol"]] = relationship(
        "Symbol", back_populates="drawing", cascade="all, delete-orphan"
    )
    lines: Mapped[list["Line"]] = relationship(
        "Line", back_populates="drawing", cascade="all, delete-orphan"
    )
    text_annotations: Mapped[list["TextAnnotation"]] = relationship(
        "TextAnnotation", back_populates="drawing", cascade="all, delete-orphan"
    )

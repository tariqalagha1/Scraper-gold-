"""Export model for generated export files.

Defines the Export entity representing exported data files
in various formats (Excel, PDF, Word).
"""
import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import DateTime, ForeignKey, Integer, String, func, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.result import Result
    from app.models.run import Run


class Export(Base):
    """Export model representing generated export files.
    
    Attributes:
        id: Unique identifier (UUID).
        result_id: Foreign key to the source result (nullable).
        run_id: Foreign key to the source run (nullable).
        format: Export format (excel, pdf, word).
        file_path: Path to the exported file.
        file_size: Size of the file in bytes.
        created_at: Timestamp when export was created.
        result: Relationship to the source result.
        run: Relationship to the source run.
    """
    
    __tablename__ = "exports"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )
    result_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("results.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    run_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("runs.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    format: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        index=True,
    )
    file_path: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
    )
    file_size: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    # Relationships
    result: Mapped[Optional["Result"]] = relationship(
        "Result",
        back_populates="exports",
        lazy="selectin",
        foreign_keys=[result_id],
    )
    run: Mapped[Optional["Run"]] = relationship(
        "Run",
        back_populates="exports",
        lazy="selectin",
        foreign_keys=[run_id],
    )

    def __repr__(self) -> str:
        """String representation of the export."""
        return f"<Export(id={self.id}, format={self.format}, file_path={self.file_path})>"

    @property
    def is_excel(self) -> bool:
        """Check if export is Excel format."""
        return self.format == "excel"

    @property
    def is_pdf(self) -> bool:
        """Check if export is PDF format."""
        return self.format == "pdf"

    @property
    def is_word(self) -> bool:
        """Check if export is Word format."""
        return self.format == "word"

    @property
    def file_size_kb(self) -> Optional[float]:
        """Get file size in kilobytes."""
        if self.file_size is not None:
            return self.file_size / 1024
        return None

    @property
    def file_size_mb(self) -> Optional[float]:
        """Get file size in megabytes."""
        if self.file_size is not None:
            return self.file_size / (1024 * 1024)
        return None

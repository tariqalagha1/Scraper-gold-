"""Result model for scraped data.

Defines the Result entity representing extracted data from a single
page or URL, including raw HTML and screenshot paths.
"""
import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any, Dict, List, Optional

from sqlalchemy import DateTime, ForeignKey, String, Text, func, text
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.export import Export
    from app.models.run import Run


class Result(Base):
    """Result model representing scraped data from a single URL.
    
    Attributes:
        id: Unique identifier (UUID).
        run_id: Foreign key to the parent run.
        data_json: Extracted data as JSON.
        data_type: Type of data extracted (maps to scraping type).
        raw_html_path: Path to stored raw HTML file.
        screenshot_path: Path to stored screenshot image.
        url: Source URL where data was extracted from.
        created_at: Timestamp when result was created.
        run: Relationship to the parent run.
        exports: List of exports generated from this result.
    """
    
    __tablename__ = "results"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )
    run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("runs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    data_json: Mapped[Dict[str, Any]] = mapped_column(
        JSON,
        nullable=False,
        default=dict,
    )
    data_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
    )
    raw_html_path: Mapped[Optional[str]] = mapped_column(
        String(500),
        nullable=True,
    )
    screenshot_path: Mapped[Optional[str]] = mapped_column(
        String(500),
        nullable=True,
    )
    url: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    # Relationships
    run: Mapped["Run"] = relationship(
        "Run",
        back_populates="results",
        lazy="selectin",
    )
    exports: Mapped[List["Export"]] = relationship(
        "Export",
        back_populates="result",
        lazy="selectin",
        cascade="all, delete-orphan",
        foreign_keys="Export.result_id",
    )

    def __repr__(self) -> str:
        """String representation of the result."""
        return f"<Result(id={self.id}, url={self.url[:50]}..., data_type={self.data_type})>"

    @property
    def has_raw_html(self) -> bool:
        """Check if raw HTML is available."""
        return self.raw_html_path is not None

    @property
    def has_screenshot(self) -> bool:
        """Check if screenshot is available."""
        return self.screenshot_path is not None

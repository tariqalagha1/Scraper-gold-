"""Run model for job execution instances.

Defines the Run entity representing a single execution of a scraping job,
tracking status, timing, progress, and results.
"""
import uuid
from datetime import datetime
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text, func, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.export import Export
    from app.models.job import Job
    from app.models.result import Result


class Run(Base):
    """Run model representing a single execution of a scraping job.
    
    Attributes:
        id: Unique identifier (UUID).
        job_id: Foreign key to the parent job.
        status: Current status (pending, running, completed, failed).
        progress: Progress percentage from 0 to 100.
        started_at: Timestamp when run started.
        finished_at: Timestamp when run completed.
        error_message: Error message if the run failed.
        error: Legacy error field retained for backward compatibility.
        pages_scraped: Number of pages successfully scraped.
        created_at: Timestamp when run was created.
        job: Relationship to the parent job.
        results: List of results from this run.
        exports: List of exports generated from this run.
    """
    
    __tablename__ = "runs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )
    job_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("jobs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="pending",
        server_default=text("'pending'"),
        index=True,
    )
    progress: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default=text("0"),
    )
    started_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    finished_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    error: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )
    error_message: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )
    pages_scraped: Mapped[int] = mapped_column(
        Integer,
        default=0,
        server_default=text("0"),
    )
    token_compression_ratio: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True,
    )
    stealth_engaged: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default=text("false"),
    )
    markdown_snapshot_path: Mapped[Optional[str]] = mapped_column(
        String(500),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    # Relationships
    job: Mapped["Job"] = relationship(
        "Job",
        back_populates="runs",
        lazy="selectin",
    )
    results: Mapped[List["Result"]] = relationship(
        "Result",
        back_populates="run",
        lazy="selectin",
        cascade="all, delete-orphan",
    )
    exports: Mapped[List["Export"]] = relationship(
        "Export",
        back_populates="run",
        lazy="selectin",
        cascade="all, delete-orphan",
        foreign_keys="Export.run_id",
    )

    def __repr__(self) -> str:
        """String representation of the run."""
        return f"<Run(id={self.id}, job_id={self.job_id}, status={self.status})>"

    @property
    def is_running(self) -> bool:
        """Check if run is currently in progress."""
        return self.status == "running"

    @property
    def is_completed(self) -> bool:
        """Check if run has finished (success or failure)."""
        return self.status in ("completed", "failed")

    @property
    def duration_seconds(self) -> Optional[float]:
        """Calculate run duration in seconds."""
        if self.started_at and self.finished_at:
            return (self.finished_at - self.started_at).total_seconds()
        return None

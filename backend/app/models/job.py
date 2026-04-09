"""Job model for scraping tasks.

Defines the Job entity representing a scraping job configuration
with URL, authentication details, and status tracking.
"""
import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any, Dict, List, Optional

from sqlalchemy import DateTime, ForeignKey, String, Text, func, text
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.secrets import EncryptedText
from app.db.base import Base

if TYPE_CHECKING:
    from app.models.run import Run
    from app.models.user import User


class Job(Base):
    """Job model representing a scraping task configuration.
    
    Attributes:
        id: Unique identifier (UUID).
        user_id: Foreign key to the user who created the job.
        url: Target URL to scrape.
        login_url: Optional URL for login page.
        login_username: Optional username for authentication.
        login_password: Optional encrypted password for authentication.
        scrape_type: Type of scraping (general, articles, products, etc.).
        config: JSON configuration for the scraping job.
        status: Current status (pending, running, completed, failed, cancelled).
        created_at: Timestamp when job was created.
        updated_at: Timestamp of last update.
        user: Relationship to the owning user.
        runs: List of execution runs for this job.
    """
    
    __tablename__ = "jobs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    url: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    login_url: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )
    login_username: Mapped[Optional[str]] = mapped_column(
        EncryptedText(),
        nullable=True,
    )
    login_password: Mapped[Optional[str]] = mapped_column(
        EncryptedText(),
        nullable=True,
    )
    scrape_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="general",
        server_default=text("'general'"),
    )
    config: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSON,
        nullable=True,
    )
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="pending",
        server_default=text("'pending'"),
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        onupdate=func.now(),
        nullable=True,
    )

    # Relationships
    user: Mapped["User"] = relationship(
        "User",
        back_populates="jobs",
        lazy="selectin",
    )
    runs: Mapped[List["Run"]] = relationship(
        "Run",
        back_populates="job",
        lazy="selectin",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        """String representation of the job."""
        return f"<Job(id={self.id}, url={self.url[:50]}..., status={self.status})>"

    @property
    def is_running(self) -> bool:
        """Check if job is currently running."""
        return self.status == "running"

    @property
    def is_completed(self) -> bool:
        """Check if job has completed (success or failure)."""
        return self.status in ("completed", "failed", "cancelled")

"""Log model for agent action logs.

Defines the Log entity for persisting agent execution logs
including input, output, errors, and timing information.
"""
import uuid
from datetime import datetime
from typing import Any, Dict, Optional

from sqlalchemy import DateTime, Float, String, Text, func, text
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Log(Base):
    """Log model for persisting agent action logs.
    
    Follows AGENT_RULES.md requirements for logging:
    - input
    - output
    - errors
    - execution time
    
    Attributes:
        id: Unique identifier (UUID).
        agent_name: Name of the agent that generated the log.
        action: The action performed by the agent.
        input_data: Input data for the action (JSON).
        output_data: Output data from the action (JSON).
        error: Error message if the action failed.
        status: Status of the action (success, fail).
        execution_time: Execution time in seconds.
        created_at: Timestamp when log was created.
    """
    
    __tablename__ = "logs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )
    agent_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,
    )
    action: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )
    input_data: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSON,
        nullable=True,
    )
    output_data: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSON,
        nullable=True,
    )
    error: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="success",
        index=True,
    )
    execution_time: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        index=True,
    )

    def __repr__(self) -> str:
        """String representation of the log."""
        return f"<Log(id={self.id}, agent={self.agent_name}, action={self.action}, status={self.status})>"

    @property
    def is_success(self) -> bool:
        """Check if the logged action was successful."""
        return self.status == "success"

    @property
    def is_failure(self) -> bool:
        """Check if the logged action failed."""
        return self.status == "fail"

    def to_dict(self) -> Dict[str, Any]:
        """Convert log to dictionary format.
        
        Returns:
            Dictionary representation following AGENT_RULES.md format.
        """
        return {
            "id": str(self.id),
            "status": self.status,
            "data": {
                "input": self.input_data,
                "output": self.output_data,
            },
            "error": self.error,
            "metadata": {
                "agent": self.agent_name,
                "action": self.action,
                "timestamp": self.created_at.isoformat() if self.created_at else None,
                "execution_time": self.execution_time,
            },
        }

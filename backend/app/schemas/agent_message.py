"""Agent message schema enforcing AGENT_RULES.md structured JSON communication.

All agents MUST use this schema for inter-agent communication.
The format ensures consistent, structured responses throughout the pipeline.

Communication Format (from AGENT_RULES.md):
{
    "status": "success|fail",
    "data": {},
    "error": null,
    "metadata": {
        "agent": "agent_name",
        "timestamp": "ISO8601"
    }
}
"""
from datetime import datetime, timezone
from typing import Any, Optional

from pydantic import BaseModel, Field


class AgentMetadata(BaseModel):
    """Metadata included with every agent response.
    
    Attributes:
        agent: Identifier of the sending agent
        timestamp: ISO8601 formatted timestamp of when response was generated
    """
    agent: str = Field(..., description="Identifier of the sending agent")
    timestamp: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
        description="ISO8601 timestamp of response generation"
    )
    source: str = Field(default="", description="Primary source URL or origin for the result")
    type: str = Field(default="generic", description="Structured result type for downstream consumers")
    execution_time: str = Field(default="0.000000", description="Execution time in seconds")


class AgentMessage(BaseModel):
    """Mandatory JSON communication schema from AGENT_RULES.md.
    
    All agents must use this format for structured communication.
    This ensures:
    - Consistent status reporting (success/fail)
    - Structured data payload
    - Error message propagation
    - Traceability via metadata
    
    Attributes:
        status: Execution status - either "success" or "fail"
        data: Payload data returned by the agent
        error: Error message if status is "fail", null otherwise
        metadata: Agent metadata including name and timestamp
    """
    status: str = Field(..., pattern="^(success|fail)$", description="success or fail")
    data: dict[str, Any] = Field(default_factory=dict, description="Payload data")
    error: Optional[str] = Field(default=None, description="Error message if status is fail")
    metadata: AgentMetadata = Field(..., description="Agent metadata for traceability")
    
    @classmethod
    def success(cls, agent_name: str, data: dict[str, Any] | None = None) -> "AgentMessage":
        """Create a success response message.
        
        Args:
            agent_name: Name of the agent generating the response
            data: Optional payload data to include
            
        Returns:
            AgentMessage with status="success"
        """
        return cls(
            status="success",
            data=data or {},
            error=None,
            metadata=AgentMetadata(agent=agent_name)
        )
    
    @classmethod
    def fail(cls, agent_name: str, error: str, data: dict[str, Any] | None = None) -> "AgentMessage":
        """Create a failure response message.
        
        Args:
            agent_name: Name of the agent generating the response
            error: Error message describing what went wrong
            data: Optional partial data to include
            
        Returns:
            AgentMessage with status="fail"
        """
        return cls(
            status="fail",
            data=data or {},
            error=error,
            metadata=AgentMetadata(agent=agent_name)
        )
    
    def is_success(self) -> bool:
        """Check if this message represents a successful operation.
        
        Returns:
            True if status is "success", False otherwise
        """
        return self.status == "success"
    
    def is_failure(self) -> bool:
        """Check if this message represents a failed operation.
        
        Returns:
            True if status is "fail", False otherwise
        """
        return self.status == "fail"
    
    def to_dict(self) -> dict[str, Any]:
        """Convert message to dictionary format.
        
        Returns:
            Dictionary representation of the message
        """
        return self.model_dump()
    
    def get_data(self, key: str, default: Any = None) -> Any:
        """Safely get a value from the data payload.
        
        Args:
            key: Key to look up in data
            default: Default value if key not found
            
        Returns:
            Value from data or default
        """
        return self.data.get(key, default)

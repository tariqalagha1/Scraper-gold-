"""Run request/response schemas.

Defines Pydantic models for scraping run operations.
"""
from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, Field

from app.schemas.execution_contract import ExecutionContract


class RunResponse(BaseModel):
    """Schema for run response data."""
    
    id: UUID = Field(..., description="Run's unique identifier")
    job_id: UUID = Field(..., description="Parent job's ID")
    status: str = Field(..., description="Current run status")
    progress: int = Field(default=0, description="Run progress percentage")
    started_at: Optional[datetime] = Field(None, description="Run start timestamp")
    finished_at: Optional[datetime] = Field(None, description="Run completion timestamp")
    error_message: Optional[str] = Field(None, description="Error message if failed")
    error: Optional[str] = Field(None, description="Legacy error message field")
    pages_scraped: int = Field(default=0, description="Number of pages scraped")
    token_compression_ratio: Optional[float] = Field(
        None,
        description="Ratio of semantic markdown size to raw HTML size",
    )
    stealth_engaged: bool = Field(
        default=False,
        description="Whether stealth mode was enabled for this run",
    )
    markdown_snapshot_path: Optional[str] = Field(
        None,
        description="Relative path to persisted semantic markdown snapshot",
    )
    created_at: datetime = Field(..., description="Run creation timestamp")
    trace_id: Optional[str] = Field(None, description="Execution trace ID for control and observability")
    execution_contract: Optional[dict[str, Any]] = Field(
        None,
        description="Validated execution contract used by this run",
    )
    execution_result: Optional[dict[str, Any]] = Field(
        None,
        description="Persisted execution result snapshot for this run",
    )
    
    model_config = {"from_attributes": True}


class RunListResponse(BaseModel):
    """Schema for paginated run list response."""
    
    runs: list[RunResponse] = Field(..., description="List of runs")
    total: int = Field(..., description="Total number of runs")


class RunQueuedResponse(BaseModel):
    id: UUID = Field(..., description="Run's unique identifier (backward-compatible field)")
    run_id: UUID = Field(..., description="Run's unique identifier")
    job_id: UUID = Field(..., description="Parent job's ID")
    trace_id: str = Field(..., description="Execution trace ID")
    status: str = Field(..., description="Current run status")
    progress: int = Field(default=0, description="Run progress percentage")
    started_at: Optional[datetime] = Field(None, description="Run start timestamp")
    finished_at: Optional[datetime] = Field(None, description="Run completion timestamp")
    error_message: Optional[str] = Field(None, description="Error message if failed")


class RunExecutionStatusResponse(BaseModel):
    run_id: UUID = Field(..., description="Run's unique identifier")
    job_id: UUID = Field(..., description="Parent job's ID")
    trace_id: Optional[str] = Field(None, description="Execution trace ID")
    status: str = Field(..., description="Current execution status")
    result: dict[str, Any] = Field(default_factory=dict, description="Execution result payload")
    errors: list[str] = Field(default_factory=list, description="Execution errors")
    started_at: Optional[str] = Field(None, description="Execution start timestamp")
    finished_at: Optional[str] = Field(None, description="Execution finish timestamp")
    execution_contract: Optional[dict[str, Any]] = Field(
        None,
        description="Execution contract applied to this run",
    )


class RunStartRequest(BaseModel):
    execution_contract: ExecutionContract = Field(
        ...,
        description="Strict contract that defines how this run will execute",
    )

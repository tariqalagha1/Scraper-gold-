"""Run request/response schemas.

Defines Pydantic models for scraping run operations.
"""
from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


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
    
    model_config = {"from_attributes": True}


class RunListResponse(BaseModel):
    """Schema for paginated run list response."""
    
    runs: list[RunResponse] = Field(..., description="List of runs")
    total: int = Field(..., description="Total number of runs")

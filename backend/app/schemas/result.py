"""Result request/response schemas.

Defines Pydantic models for scraped result operations.
"""
from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class ResultResponse(BaseModel):
    """Schema for result response data."""
    
    id: UUID = Field(..., description="Result's unique identifier")
    run_id: UUID = Field(..., description="Parent run's ID")
    data_json: dict[str, Any] = Field(..., description="Extracted data as JSON")
    data_type: str = Field(..., description="Type of data extracted")
    url: str = Field(..., description="Source URL of the data")
    raw_html_path: Optional[str] = Field(None, description="Path to stored raw HTML")
    screenshot_path: Optional[str] = Field(None, description="Path to stored screenshot")
    created_at: datetime = Field(..., description="Result creation timestamp")
    
    model_config = {"from_attributes": True}


class ResultCreate(BaseModel):
    """Schema for persisting a result record."""

    run_id: UUID = Field(..., description="Parent run's ID")
    data_json: dict[str, Any] = Field(..., description="Extracted data as JSON")
    data_type: str = Field(..., description="Type of data extracted")
    url: str = Field(..., description="Source URL of the data")
    raw_html_path: Optional[str] = Field(None, description="Path to stored raw HTML")
    screenshot_path: Optional[str] = Field(None, description="Path to stored screenshot")


class ResultSearch(BaseModel):
    """Schema for filtering result queries."""

    query: str = Field(default="", description="Search query text")
    data_type: Optional[str] = Field(None, description="Optional extracted data type filter")
    run_id: Optional[UUID] = Field(None, description="Optional parent run filter")
    job_id: Optional[UUID] = Field(None, description="Optional parent job filter")
    use_semantic_search: bool = Field(default=False, description="Whether to use vector search")


class ResultListResponse(BaseModel):
    """Schema for paginated result list response."""
    
    results: list[ResultResponse] = Field(..., description="List of results")
    total: int = Field(..., description="Total number of results")

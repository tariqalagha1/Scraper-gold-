"""Export request/response schemas.

Defines Pydantic models for export operations.
"""
from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


class ExportCreate(BaseModel):
    """Schema for creating a new export."""
    
    run_id: UUID = Field(..., description="Run ID containing results to export")
    format: str = Field(
        ...,
        pattern="^(excel|pdf|word|json)$",
        description="Export format (excel, pdf, word, or json)"
    )


class ExportResponse(BaseModel):
    """Schema for export response data."""
    
    id: UUID = Field(..., description="Export's unique identifier")
    run_id: Optional[UUID] = Field(None, description="Source run's ID")
    result_id: Optional[UUID] = Field(None, description="Source result's ID")
    format: str = Field(..., description="Export file format")
    file_path: str = Field(..., description="Path to the export file")
    file_size: Optional[int] = Field(None, description="File size in bytes")
    created_at: datetime = Field(..., description="Export creation timestamp")
    
    model_config = {"from_attributes": True}


class ExportListResponse(BaseModel):
    """Schema for paginated export list response."""
    
    exports: list[ExportResponse] = Field(..., description="List of exports")
    total: int = Field(..., description="Total number of exports")

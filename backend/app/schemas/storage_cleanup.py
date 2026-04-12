from __future__ import annotations

from pydantic import BaseModel, Field


class HistoryCleanupEstimate(BaseModel):
    search_history: int = Field(0)
    prompt_history: int = Field(0)
    previous_runs: int = Field(0)
    generated_reports_metadata: int = Field(0)
    recent_activity_log: int = Field(0)
    total_records: int = Field(0)


class TempFilesCleanupEstimate(BaseModel):
    cached_exports: int = Field(0)
    temp_markdown: int = Field(0)
    temp_pdfs: int = Field(0)
    image_cache: int = Field(0)
    processing_temp_files: int = Field(0)
    orphaned_uploads: int = Field(0)
    stale_session_artifacts: int = Field(0)
    total_files: int = Field(0)
    estimated_freed_space_mb: float = Field(0.0)


class StorageCleanupEstimateResponse(BaseModel):
    history: HistoryCleanupEstimate
    temp_files: TempFilesCleanupEstimate


class CleanupResultResponse(BaseModel):
    status: str = Field(..., description="Cleanup execution status")
    deleted_history_records: int = Field(0)
    deleted_temp_files: int = Field(0)
    freed_space_mb: float = Field(0.0)
    deleted_items_count: int = Field(0)
    cleared_scopes: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)

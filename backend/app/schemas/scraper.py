"""Schemas for Brain it <-> Smart Scraper agent integration."""
from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator

from app.core.security_guard import normalize_and_validate_prompt, normalize_untrusted_text


class ScraperTaskInputPayload(BaseModel):
    url: str | None = Field(default=None, max_length=2000)
    login_url: str | None = Field(default=None, max_length=2000)
    login_username: str | None = Field(default=None, max_length=200)
    login_password: str | None = Field(default=None, max_length=200)
    query: str = Field(..., min_length=1, max_length=500)
    location: str = Field(..., min_length=1, max_length=200)
    limit: int = Field(default=50, ge=1, le=500)
    fields: list[str] = Field(..., min_length=1, max_length=50)
    source_type: str | None = Field(default=None, max_length=100)
    request_id: str | None = Field(default=None, max_length=120)

    @field_validator("query", mode="before")
    @classmethod
    def _normalize_query(cls, value: object) -> object:
        if isinstance(value, str):
            return normalize_and_validate_prompt(value)
        return value

    @field_validator(
        "url",
        "login_url",
        "login_username",
        "login_password",
        "location",
        "source_type",
        "request_id",
        mode="before",
    )
    @classmethod
    def _normalize_text_fields(cls, value: object) -> object:
        if isinstance(value, str):
            max_chars = 2000 if len(value) > 200 else 200
            return normalize_untrusted_text(value, max_chars=max_chars).strip()
        return value

    @field_validator("fields")
    @classmethod
    def _normalize_fields(cls, value: list[str]) -> list[str]:
        cleaned: list[str] = []
        for item in value:
            text = normalize_untrusted_text(str(item), max_chars=100).strip()
            if text:
                cleaned.append(text)
        if not cleaned:
            raise ValueError("fields must contain at least one non-empty field")
        return cleaned


class BrainItScrapeTaskRequest(BaseModel):
    task_type: Literal["scrape"] = "scrape"
    input_payload: ScraperTaskInputPayload
    task_id: str | None = Field(default=None, max_length=120)

    @field_validator("task_id", mode="before")
    @classmethod
    def _normalize_task_id(cls, value: object) -> object:
        if isinstance(value, str):
            return normalize_untrusted_text(value, max_chars=120).strip()
        return value


class ScraperSourceItem(BaseModel):
    name: str = Field(..., min_length=1)
    count: int = Field(default=0, ge=0)


class ScraperQualityMetadata(BaseModel):
    duplicates_removed: int = Field(default=0, ge=0)
    coverage: float = Field(default=0.0, ge=0.0, le=1.0)
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    missing_fields: dict[str, int] = Field(default_factory=dict)
    normalized_fields: int | None = Field(default=None, ge=0)


class SmartScraperResponse(BaseModel):
    request_id: str = Field(..., min_length=1)
    status: str
    execution_time: float = Field(default=0.0, ge=0.0)
    total: int = Field(default=0, ge=0)
    data: list[dict[str, Any]] = Field(default_factory=list)
    sources: list[ScraperSourceItem] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
    quality: ScraperQualityMetadata


class ScraperAgentSummary(BaseModel):
    total: int = Field(default=0, ge=0)
    coverage: float = Field(default=0.0, ge=0.0, le=1.0)
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)


class ScraperAgentOutputPayload(BaseModel):
    data: list[dict[str, Any]] = Field(default_factory=list)
    sources: list[ScraperSourceItem] = Field(default_factory=list)
    quality: ScraperQualityMetadata
    errors: list[str] = Field(default_factory=list)
    request_id: str = Field(..., min_length=1)
    execution_time: float = Field(default=0.0, ge=0.0)


class ScraperAgentInsights(BaseModel):
    summary: str = Field(default="")
    key_findings: list[str] = Field(default_factory=list)
    data_quality_note: str = Field(default="")
    recommended_next_step: str = Field(default="")


class ScraperAgentMetadata(BaseModel):
    service: str = "smart-scraper"
    task_type: str = "scrape"


class ScraperExecutionStep(BaseModel):
    step: int = Field(..., ge=1)
    agent: str = "scraper_agent"
    service: str = "smart-scraper"
    input_summary: dict[str, Any] = Field(default_factory=dict)
    output_summary: dict[str, Any] = Field(default_factory=dict)
    status: str


class ScraperAgentNormalizedResult(BaseModel):
    agent: str = "scraper_agent"
    status: Literal["completed", "partial", "failed"]
    summary: ScraperAgentSummary
    output_payload: ScraperAgentOutputPayload
    insights: ScraperAgentInsights
    execution_steps: list[ScraperExecutionStep] = Field(default_factory=list)
    metadata: ScraperAgentMetadata = Field(default_factory=ScraperAgentMetadata)
    scraper_confidence: float = Field(default=0.0, ge=0.0, le=1.0)


class AgentRegistryEntry(BaseModel):
    name: str
    description: str
    supported_task_types: list[str]
    service_identifier: str
    endpoint: str
    health_url: str
    status: Literal["enabled", "disabled"] = "enabled"
    enabled: bool = True

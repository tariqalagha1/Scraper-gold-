"""Canonical scrape endpoint schemas for external integrations."""
from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field, field_validator, model_validator

from app.core.security_guard import normalize_and_validate_prompt, normalize_untrusted_text


class ScrapeRequest(BaseModel):
    workspace_type: str = Field(default="url", max_length=50) # 'url' or 'maps'
    url: str | None = Field(default=None, max_length=2000)
    login_url: str | None = Field(default=None, max_length=2000)
    login_username: str | None = Field(default=None, max_length=200)
    login_password: str | None = Field(default=None, max_length=200)
    query: str = Field(..., min_length=1, max_length=500)
    location: str = Field(..., min_length=1, max_length=200)
    limit: int = Field(default=50, ge=1, le=100) # corresponds to target_records
    target_records: int | None = Field(default=None, ge=1, le=100)
    entity_type: str | None = Field(default=None, max_length=100)
    fields: list[str] = Field(..., min_length=1, max_length=50)
    required_fields: list[str] = Field(default_factory=list, max_length=50)
    minimum_completeness: int = Field(default=0, ge=0, le=100)
    source_type: str | None = Field(default=None, max_length=100)
    request_id: str | None = Field(default=None, max_length=120)
    sources: list[str] = Field(default_factory=lambda: ["internal"])
    force_sources: bool = Field(default=False)
    strict_extraction: bool = Field(default=True)

    @model_validator(mode='after')
    def validate_workspace_and_sources(self) -> 'ScrapeRequest':
        # Keep backwards compatibility with existing multi-source behavior.
        if not self.sources:
            self.sources = ["internal"]

        allowed_sources = {"internal", "google_maps", "web"}
        for src in self.sources:
            if src not in allowed_sources:
                raise ValueError(
                    f"Source '{src}' is not supported. Allowed: {sorted(allowed_sources)}"
                )
                
        # Sync limit and target_records
        if self.target_records is not None:
            self.limit = self.target_records
        else:
            self.target_records = self.limit
            
        return self

    @field_validator("query", mode="before")
    @classmethod
    def _validate_query_prompt_guard(cls, value: object) -> object:
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
        "entity_type",
        "workspace_type",
        mode="before",
    )
    @classmethod
    def _strip_text_fields(cls, value: object) -> object:
        if isinstance(value, str):
            max_chars = 2000 if len(value) > 200 else 200
            return normalize_untrusted_text(value, max_chars=max_chars).strip()
        return value

    @field_validator("fields", "required_fields")
    @classmethod
    def _validate_fields(cls, value: list[str]) -> list[str]:
        cleaned: list[str] = []
        for item in value:
            text = normalize_untrusted_text(str(item), max_chars=100).strip()
            if not text:
                continue
            cleaned.append(text)
        return cleaned


class ScrapeQualityMetadata(BaseModel):
    duplicates_removed: int = Field(default=0, ge=0)
    coverage: float = Field(default=0.0, ge=0.0, le=1.0)
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    missing_fields: dict[str, int] = Field(default_factory=dict)
    normalized_fields: int | None = Field(default=None, ge=0)
    sources_used: list[str] = Field(default_factory=list)
    sources_skipped: list[str] = Field(default_factory=list)
    execution_order: list[str] = Field(default_factory=list)
    cross_source_duplicates_removed: int = Field(default=0, ge=0)
    source_reliability: dict[str, float] = Field(default_factory=dict)
    execution_tiers: dict[str, list[str]] = Field(default_factory=dict)
    tiers_executed: list[str] = Field(default_factory=list)
    early_stopped: bool = Field(default=False)
    fallback_used: bool = Field(default=False)
    retries_triggered: list[str] = Field(default_factory=list)
    policy: dict[str, Any] = Field(default_factory=dict)


class ScrapeSource(BaseModel):
    name: str = Field(..., min_length=1)
    count: int = Field(default=0, ge=0)


class ScrapeResponse(BaseModel):
    request_id: str = Field(..., min_length=1)
    status: str
    execution_time: float = Field(default=0.0, ge=0.0)
    total: int = Field(default=0, ge=0)
    data: list[dict[str, Any]]
    sources: list[ScrapeSource]
    errors: list[str]
    quality: ScrapeQualityMetadata

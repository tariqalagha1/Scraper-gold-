"""Assistant chat schemas used for request refinement."""
from __future__ import annotations

from typing import Literal

from pydantic import AnyHttpUrl, BaseModel, ConfigDict, Field, field_validator

from app.core.security_guard import normalize_untrusted_text
from app.schemas.scraping_types import ScrapingType


class AssistantChatMessage(BaseModel):
    """Single conversation message exchanged with the assistant."""

    model_config = ConfigDict(extra="forbid")

    role: Literal["user", "assistant"] = Field(..., description="Speaker role")
    content: str = Field(..., min_length=1, max_length=4000, description="Message body")

    @field_validator("content", mode="before")
    @classmethod
    def normalize_content(cls, value: object) -> object:
        if not isinstance(value, str):
            return value
        return normalize_untrusted_text(value, max_chars=4000)


class AssistantRefinementRequest(BaseModel):
    """Incoming request for AI-assisted scrape request refinement."""

    model_config = ConfigDict(extra="forbid")

    url: AnyHttpUrl | None = Field(default=None, description="Target website URL")
    draft_prompt: str | None = Field(
        default=None,
        max_length=2000,
        description="Current draft prompt from the user",
    )
    user_message: str = Field(..., min_length=1, max_length=2000, description="Latest user message")
    conversation: list[AssistantChatMessage] = Field(
        default_factory=list,
        max_length=16,
        description="Recent chat turns (oldest to newest)",
    )

    @field_validator("draft_prompt", "user_message", mode="before")
    @classmethod
    def normalize_prompt_like_fields(cls, value: object) -> object:
        if value is None or not isinstance(value, str):
            return value
        normalized = normalize_untrusted_text(value, max_chars=2000)
        return normalized or None


class AssistantRefinementResponse(BaseModel):
    """Response returned to the dashboard chat assistant."""

    assistant_message: str = Field(..., description="Natural-language guidance for the user")
    refined_prompt: str = Field(..., description="Structured final prompt recommended by the assistant")
    recommended_scrape_type: ScrapingType = Field(..., description="Suggested scrape type")
    ready_to_apply: bool = Field(..., description="Whether the prompt is complete enough to run")
    clarifying_questions: list[str] = Field(default_factory=list, description="Questions to resolve ambiguity")
    suggestions: list[str] = Field(default_factory=list, description="Short actionable suggestions")
    source: Literal["openai", "heuristic"] = Field(
        default="heuristic",
        description="Response generation backend",
    )

"""Job request/response schemas.

Defines Pydantic models for scraping job operations including
login credentials and scraping configuration.
"""
from datetime import datetime
from typing import Literal, Optional
from uuid import UUID

from pydantic import AnyHttpUrl, BaseModel, ConfigDict, Field, ValidationInfo, field_validator, model_validator
from pydantic_core import PydanticCustomError

from app.core.security_guard import normalize_and_validate_prompt, validate_scrape_url
from app.schemas.scraping_types import ScrapingType


class JobConfigSchema(BaseModel):
    """Strictly-typed job configuration payload."""

    model_config = ConfigDict(extra="forbid")

    prompt: Optional[str] = Field(
        default=None,
        max_length=2000,
        description="Natural-language extraction request",
    )
    max_pages: Optional[int] = Field(
        default=None,
        ge=1,
        le=1000,
        description="Maximum number of pages to scrape",
    )
    follow_pagination: Optional[bool] = Field(
        default=None,
        description="Whether to follow pagination links",
    )
    follow_links: Optional[bool] = Field(
        default=None,
        description="Legacy alias for follow_pagination",
    )
    max_depth: Optional[int] = Field(
        default=None,
        ge=0,
        le=10,
        description="Maximum traversal depth (when used)",
    )
    respect_robots_txt: Optional[bool] = Field(
        default=True,
        description="Whether scraping should honor robots.txt",
    )
    rate_limit_delay: Optional[float] = Field(
        default=None,
        ge=0.0,
        le=60.0,
        description="Delay between requests in seconds",
    )
    delay: Optional[float] = Field(
        default=None,
        ge=0.0,
        le=60.0,
        description="Legacy alias for rate_limit_delay",
    )
    timeout_ms: Optional[int] = Field(
        default=None,
        ge=0,
        le=300_000,
        description="Navigation timeout in milliseconds",
    )
    wait_for_selector: Optional[str] = Field(
        default=None,
        max_length=500,
        description="Optional CSS selector to wait for",
    )
    wait_for_selector_timeout_ms: Optional[int] = Field(
        default=None,
        ge=0,
        le=300_000,
        description="Timeout for wait_for_selector in milliseconds",
    )
    wait_until: Optional[Literal["load", "domcontentloaded", "networkidle", "commit"]] = Field(
        default=None,
        description="Playwright waitUntil mode for navigation",
    )
    post_navigation_wait_until: Optional[Literal["load", "domcontentloaded", "networkidle", "commit"]] = Field(
        default=None,
        description="Playwright waitUntil mode after initial navigation",
    )
    user_agent: Optional[str] = Field(
        default=None,
        max_length=500,
        description="Optional browser user-agent override",
    )
    viewport_width: Optional[int] = Field(
        default=None,
        ge=200,
        le=8000,
        description="Browser viewport width",
    )
    viewport_height: Optional[int] = Field(
        default=None,
        ge=200,
        le=8000,
        description="Browser viewport height",
    )
    pagination_type: Optional[Literal["auto", "next", "load_more", "scroll"]] = Field(
        default=None,
        description="Pagination strategy",
    )
    follow_detail_pages: Optional[bool] = Field(
        default=None,
        description="Whether to follow detail pages from listing pages",
    )
    detail_link_selector: Optional[str] = Field(
        default=None,
        max_length=500,
        description="CSS selector used to find detail-page links",
    )
    traversal_mode: Optional[Literal["auto", "list_harvest", "detail_drill", "single_detail"]] = Field(
        default=None,
        description="Traversal mode hint",
    )
    detail_page_limit: Optional[int] = Field(
        default=None,
        ge=1,
        le=1000,
        description="Maximum number of detail pages to visit",
    )
    detail_stop_rule: Optional[Literal["budget_only", "duplicate_title"]] = Field(
        default=None,
        description="Rule used to stop detail-page traversal",
    )
    page_hints: Optional[list[str]] = Field(
        default=None,
        description="Optional classification hints",
    )
    stealth_mode: Optional[bool] = Field(
        default=False,
        description="Enable stealth scraping mode with browser hardening",
    )
    stealth_undetected: Optional[bool] = Field(
        default=True,
        description="Enable anti-detection browser fingerprint masking",
    )
    stealth_randomize_headers: Optional[bool] = Field(
        default=True,
        description="Randomize request headers to reduce bot signatures",
    )

    @field_validator("prompt", mode="before")
    @classmethod
    def normalize_config_prompt(cls, value: object) -> object:
        if value is None:
            return None
        if isinstance(value, str):
            return normalize_and_validate_prompt(value)
        return value

    @field_validator("wait_for_selector", "detail_link_selector", "user_agent", mode="before")
    @classmethod
    def normalize_optional_strings(cls, value: object) -> object:
        if value is None:
            return None
        if isinstance(value, str):
            normalized = value.strip()
            return normalized or None
        return value

    @field_validator("page_hints", mode="before")
    @classmethod
    def normalize_page_hints(cls, value: object) -> object:
        if value is None:
            return None
        if isinstance(value, list):
            cleaned = [str(item).strip().lower() for item in value if str(item).strip()]
            return cleaned or None
        return value

    @model_validator(mode="after")
    def normalize_link_follow_flags(self) -> "JobConfigSchema":
        if self.follow_pagination is None and self.follow_links is not None:
            self.follow_pagination = self.follow_links
        elif self.follow_links is None and self.follow_pagination is not None:
            self.follow_links = self.follow_pagination
        return self


class JobCreate(BaseModel):
    """Schema for creating a new scraping job."""

    url: AnyHttpUrl = Field(..., description="Target URL to scrape")
    login_url: Optional[AnyHttpUrl] = Field(
        None,
        description="Login page URL if authentication is required",
    )
    login_username: Optional[str] = Field(
        None,
        description="Username for target site login",
    )
    login_password: Optional[str] = Field(
        None,
        description="Password for target site login",
    )
    scrape_type: ScrapingType = Field(
        default=ScrapingType.GENERAL,
        description="Type of content to scrape",
    )
    prompt: Optional[str] = Field(
        None,
        max_length=2000,
        description="User's natural-language extraction request",
    )
    max_pages: int = Field(
        default=10,
        ge=1,
        le=1000,
        description="Maximum number of pages to scrape",
    )
    follow_pagination: bool = Field(
        default=True,
        description="Whether to follow pagination links",
    )
    config: Optional[JobConfigSchema] = Field(
        None,
        description="Additional typed job configuration options",
    )

    @field_validator("prompt", mode="before")
    @classmethod
    def normalize_prompt(cls, value: object) -> object:
        if value is None:
            return None
        if isinstance(value, str):
            return normalize_and_validate_prompt(value)
        return value

    @field_validator("url", "login_url", mode="after")
    @classmethod
    def validate_target_urls(
        cls,
        value: AnyHttpUrl | None,
        info: ValidationInfo,
    ) -> AnyHttpUrl | None:
        if value is None:
            return None
        error = validate_scrape_url(str(value), field_name=info.field_name)
        if error:
            raise ValueError(error)
        return value

    @field_validator("login_username", "login_password", mode="before")
    @classmethod
    def normalize_login_strings(cls, value: object) -> object:
        if value is None:
            return None
        if isinstance(value, str):
            normalized = value.strip()
            return normalized or None
        return value

    @model_validator(mode="after")
    def validate_login_fields(self) -> "JobCreate":
        if any((self.login_url, self.login_username, self.login_password)) and not all(
            (self.login_url, self.login_username, self.login_password)
        ):
            raise PydanticCustomError(
                "incomplete_login_fields",
                "login_url, login_username, and login_password must all be provided together",
            )
        return self


class JobUpdate(BaseModel):
    """Schema for partially updating a scraping job."""

    url: Optional[AnyHttpUrl] = Field(None, description="Target URL to scrape")
    login_url: Optional[AnyHttpUrl] = Field(
        None,
        description="Login page URL if authentication is required",
    )
    login_username: Optional[str] = Field(None, description="Username for target site login")
    login_password: Optional[str] = Field(None, description="Password for target site login")
    scrape_type: Optional[ScrapingType] = Field(None, description="Type of content to scrape")
    prompt: Optional[str] = Field(
        None,
        max_length=2000,
        description="User's natural-language extraction request",
    )
    max_pages: Optional[int] = Field(
        None,
        ge=1,
        le=1000,
        description="Maximum number of pages to scrape",
    )
    follow_pagination: Optional[bool] = Field(
        None,
        description="Whether pagination is enabled",
    )
    config: Optional[dict] = Field(None, description="Additional job configuration options")

    @field_validator("prompt", mode="before")
    @classmethod
    def normalize_update_prompt(cls, value: object) -> object:
        if value is None:
            return None
        if isinstance(value, str):
            normalized = value.strip()
            if not normalized:
                return None
            return normalize_and_validate_prompt(normalized)
        return value

    @field_validator("login_username", "login_password", mode="before")
    @classmethod
    def normalize_update_login_strings(cls, value: object) -> object:
        if value is None:
            return None
        if isinstance(value, str):
            normalized = value.strip()
            return normalized or None
        return value

    @field_validator("url", "login_url", mode="after")
    @classmethod
    def validate_update_urls(
        cls,
        value: AnyHttpUrl | None,
        info: ValidationInfo,
    ) -> AnyHttpUrl | None:
        if value is None:
            return None
        error = validate_scrape_url(str(value), field_name=info.field_name)
        if error:
            raise ValueError(error)
        return value


class JobResponse(BaseModel):
    """Schema for job response data."""

    id: UUID = Field(..., description="Job's unique identifier")
    user_id: UUID = Field(..., description="Owner's user ID")
    url: str = Field(..., description="Target URL")
    login_url: Optional[str] = Field(None, description="Login page URL")
    scrape_type: str = Field(..., description="Type of content being scraped")
    prompt: Optional[str] = Field(None, description="User's natural-language extraction request")
    status: str = Field(..., description="Current job status")
    max_pages: int = Field(default=10, description="Maximum pages to scrape")
    follow_pagination: bool = Field(default=True, description="Whether pagination is enabled")
    created_at: datetime = Field(..., description="Job creation timestamp")
    updated_at: Optional[datetime] = Field(None, description="Last update timestamp")

    model_config = {"from_attributes": True}


class JobListResponse(BaseModel):
    """Schema for paginated job list response."""

    jobs: list[JobResponse] = Field(..., description="List of jobs")
    total: int = Field(..., description="Total number of jobs")

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

from app.core.security_guard import normalize_untrusted_text


class CredentialCreate(BaseModel):
    provider: str = Field(..., min_length=2, max_length=50)
    api_key: str = Field(..., min_length=1, max_length=4096)

    @field_validator("provider", mode="before")
    @classmethod
    def normalize_provider(cls, value: object) -> object:
        if isinstance(value, str):
            normalized = normalize_untrusted_text(value, max_chars=50).lower()
            return normalized
        return value

    @field_validator("api_key", mode="before")
    @classmethod
    def normalize_api_key(cls, value: object) -> object:
        if not isinstance(value, str):
            return value
        normalized = normalize_untrusted_text(value, max_chars=4096).strip()
        if not normalized:
            raise ValueError("api_key must not be empty")
        if any(ch.isspace() for ch in normalized):
            raise ValueError("api_key must not contain whitespace characters")
        return normalized


class CredentialResponse(BaseModel):
    id: UUID
    provider: str
    key_mask: str
    is_active: bool
    created_at: datetime
    updated_at: datetime | None = None

    model_config = {"from_attributes": True}


class CredentialListResponse(BaseModel):
    credentials: list[CredentialResponse]
    total: int

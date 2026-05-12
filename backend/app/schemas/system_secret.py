from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator

from app.core.security_guard import normalize_untrusted_text


class SystemSecretUpdate(BaseModel):
    value: str = Field(..., min_length=1, max_length=4000)

    @field_validator("value", mode="before")
    @classmethod
    def normalize_value(cls, value: object) -> object:
        if isinstance(value, str):
            cleaned = normalize_untrusted_text(value, max_chars=4000).strip()
            if not cleaned:
                raise ValueError("value cannot be empty")
            return cleaned
        return value


class SystemSecretItem(BaseModel):
    name: str
    configured: bool
    source: Literal["env", "database", "unset"]
    key_mask: str | None = None
    updated_at: datetime | None = None
    updated_by_email: str | None = None


class SystemSecretListResponse(BaseModel):
    secrets: list[SystemSecretItem]


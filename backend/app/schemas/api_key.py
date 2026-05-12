from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field
from pydantic import field_validator


class ApiKeyCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=120)

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("name must not be blank")
        return normalized


class ApiKeyResponse(BaseModel):
    id: UUID
    user_id: UUID
    name: str
    is_active: bool
    created_at: datetime
    key_preview: str

    model_config = {"from_attributes": True}


class ApiKeyCreateResponse(ApiKeyResponse):
    api_key: str
    key: str


class ApiKeyListResponse(BaseModel):
    api_keys: list[ApiKeyResponse]
    total: int

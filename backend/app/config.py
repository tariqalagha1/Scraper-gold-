from functools import lru_cache
import base64
import hashlib
from pathlib import Path
from typing import Literal

from pydantic import AliasChoices, AnyHttpUrl, Field, computed_field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


BASE_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=BASE_DIR / ".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    APP_NAME: str = "Smart Scraper Platform"
    APP_VERSION: str = "1.0.0"
    APP_DESCRIPTION: str = "AI-powered multi-agent web scraping SaaS platform"
    ENVIRONMENT: Literal["development", "staging", "production"] = "development"
    DEBUG: bool = False
    RELOAD: bool = False
    API_V1_PREFIX: str = "/api/v1"

    DATABASE_URL: str = "postgresql+asyncpg://scraper:scraper_password_change_me@localhost:5432/scraper_db"
    DATABASE_POOL_SIZE: int = 10
    DATABASE_MAX_OVERFLOW: int = 20
    DATABASE_POOL_TIMEOUT: int = 30
    DATABASE_POOL_RECYCLE: int = 1800
    DATABASE_CONNECT_MAX_RETRIES: int = 3
    DATABASE_CONNECT_RETRY_DELAY: float = 1.0

    REDIS_URL: str = "redis://localhost:6379/0"
    REDIS_CONNECT_TIMEOUT: float = 5.0

    SECRET_KEY: str = "your-super-secret-key-change-in-production-min-32-chars"
    API_KEY: str = ""
    API_KEY_HEADER_NAME: str = "X-API-Key"
    ALGORITHM: str = Field(
        default="HS256",
        validation_alias=AliasChoices("JWT_ALGORITHM", "ALGORITHM"),
    )
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(
        default=30,
        validation_alias=AliasChoices(
            "JWT_ACCESS_TOKEN_EXPIRE_MINUTES",
            "ACCESS_TOKEN_EXPIRE_MINUTES",
        ),
    )

    CORS_ORIGINS: list[AnyHttpUrl | str] = Field(
        default_factory=lambda: [
            "http://localhost:3000",
            "http://127.0.0.1:3000",
            "http://localhost:3001",
            "http://127.0.0.1:3001",
        ]
    )
    CORS_ORIGIN_REGEX: str | None = r"^https?://(localhost|127\.0\.0\.1)(:\d+)?$"

    STORAGE_ROOT: Path = BASE_DIR / "storage"
    EXPORT_RETENTION_HOURS: int = 168
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: Literal["json", "text"] = "json"

    PLAYWRIGHT_HEADLESS: bool = True
    PLAYWRIGHT_TIMEOUT: int = 30000
    DEFAULT_RATE_LIMIT_DELAY: float = 1.0
    REQUEST_TIMEOUT_SECONDS: int = 60
    MAX_REQUEST_SIZE_BYTES: int = 1_048_576
    ENABLE_SECURITY_HEADERS: bool = True
    ENABLE_PROMPT_INJECTION_GUARD: bool = True
    SECURITY_PROMPT_MAX_CHARS: int = 4_000
    SECURITY_PROMPT_BLOCK_THRESHOLD: int = 3
    BLOCK_PRIVATE_NETWORK_TARGETS: bool = True
    ALLOW_LOOPBACK_TARGETS_IN_NON_PRODUCTION: bool = True
    RATE_LIMIT_REQUESTS: int = 10
    RATE_LIMIT_WINDOW_SECONDS: int = 60
    JOB_CREATE_RATE_LIMIT: int = 10
    JOB_CREATE_RATE_WINDOW_SECONDS: int = 3600
    RUN_CREATE_RATE_LIMIT: int = 10
    RUN_CREATE_RATE_WINDOW_SECONDS: int = 60
    ENABLE_VECTOR: bool = False
    ANALYSIS_MODE: Literal["basic", "ai"] = "basic"
    CELERY_TASK_TIME_LIMIT: int = 300
    CELERY_TASK_SOFT_TIME_LIMIT: int = 270
    ORCHESTRATION_NODE_TIMEOUT_SECONDS: int = 90
    ORCHESTRATION_INTAKE_TIMEOUT_SECONDS: int = 30
    ORCHESTRATION_SCRAPER_TIMEOUT_SECONDS: int = 180
    ORCHESTRATION_PROCESSING_TIMEOUT_SECONDS: int = 60
    ORCHESTRATION_VECTOR_TIMEOUT_SECONDS: int = 45
    ORCHESTRATION_ANALYSIS_TIMEOUT_SECONDS: int = 45
    ORCHESTRATION_EXPORT_TIMEOUT_SECONDS: int = 45

    OPENAI_API_KEY: str = ""
    OPENAI_ORCHESTRATION_MODEL: str = "gpt-4o-mini"
    OPENAI_ANALYSIS_MODEL: str = "gpt-4o-mini"
    OPENAI_EMBEDDING_MODEL: str = "text-embedding-3-small"
    GEMINI_API_KEY: str = ""
    SUPABASE_URL: str = ""
    SUPABASE_SERVICE_ROLE_KEY: str = ""
    PROVIDER_API_KEY_ENCRYPTION_KEY: str = ""

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def parse_cors_origins(cls, value: object) -> object:
        if isinstance(value, str):
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        return value

    @field_validator("SECRET_KEY")
    @classmethod
    def validate_secret_key(cls, value: str) -> str:
        if len(value) < 32:
            raise ValueError("SECRET_KEY must be at least 32 characters long.")
        return value

    @field_validator("LOG_LEVEL")
    @classmethod
    def normalize_log_level(cls, value: str) -> str:
        return value.upper()

    @field_validator("DEBUG", "RELOAD", mode="before")
    @classmethod
    def normalize_bool_like_flags(cls, value: object) -> object:
        if isinstance(value, str):
            lowered = value.strip().lower()
            if lowered in {"1", "true", "yes", "on", "debug", "development"}:
                return True
            if lowered in {"0", "false", "no", "off", "release", "prod", "production"}:
                return False
        return value

    def validate_runtime_requirements(self) -> None:
        critical_values = {
            "DATABASE_URL": self.DATABASE_URL,
            "REDIS_URL": self.REDIS_URL,
            "SECRET_KEY": self.SECRET_KEY,
        }
        missing = [name for name, value in critical_values.items() if not str(value).strip()]
        if missing:
            raise ValueError(f"Missing required environment variables: {', '.join(missing)}")

        if self.is_production and any(str(origin).strip() == "*" for origin in self.CORS_ORIGINS):
            raise ValueError("Wildcard CORS origins are not allowed in production.")
        if self.is_production and self.CORS_ORIGIN_REGEX:
            raise ValueError("CORS_ORIGIN_REGEX is only allowed outside production.")

    @computed_field
    @property
    def is_production(self) -> bool:
        return self.ENVIRONMENT == "production"

    @computed_field
    @property
    def jwt_access_token_expire_minutes(self) -> int:
        return self.ACCESS_TOKEN_EXPIRE_MINUTES

    @computed_field
    @property
    def jwt_algorithm(self) -> str:
        return self.ALGORITHM

    @computed_field
    @property
    def resolved_provider_api_key_encryption_key(self) -> str:
        explicit = self.PROVIDER_API_KEY_ENCRYPTION_KEY.strip()
        if explicit:
            return explicit
        digest = hashlib.sha256(self.SECRET_KEY.encode("utf-8")).digest()
        return base64.urlsafe_b64encode(digest).decode("utf-8")


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()

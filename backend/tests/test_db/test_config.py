import pytest

from app.config import BASE_DIR, Settings


def test_settings_resolves_relative_sqlite_database_url_to_backend_dir():
    settings = Settings(
        DATABASE_URL="sqlite+aiosqlite:///./dev.db",
        REDIS_URL="redis://localhost:6379/0",
        SECRET_KEY="x" * 32,
    )

    assert settings.DATABASE_URL == f"sqlite+aiosqlite:///{(BASE_DIR / 'dev.db').resolve()}"


def test_settings_keeps_absolute_sqlite_database_url_unchanged():
    absolute_path = (BASE_DIR / "tmp" / "custom.db").resolve()
    settings = Settings(
        DATABASE_URL=f"sqlite+aiosqlite:///{absolute_path}",
        REDIS_URL="redis://localhost:6379/0",
        SECRET_KEY="x" * 32,
    )

    assert settings.DATABASE_URL == f"sqlite+aiosqlite:///{absolute_path}"


def test_runtime_requirements_fail_when_scraper_api_key_missing():
    settings = Settings(
        DATABASE_URL="sqlite+aiosqlite:///./dev.db",
        REDIS_URL="redis://localhost:6379/0",
        SECRET_KEY="x" * 32,
        SCRAPER_BASE_URL="http://127.0.0.1:8003",
        SCRAPER_API_KEY="",
    )

    with pytest.raises(ValueError, match="SCRAPER_API_KEY"):
        settings.validate_runtime_requirements()


def test_runtime_requirements_pass_when_scraper_api_key_present():
    settings = Settings(
        DATABASE_URL="sqlite+aiosqlite:///./dev.db",
        REDIS_URL="redis://localhost:6379/0",
        SECRET_KEY="x" * 32,
        SCRAPER_BASE_URL="http://127.0.0.1:8003",
        SCRAPER_API_KEY="provider-key-123",
    )

    settings.validate_runtime_requirements()


def test_scraper_settings_fallback_to_process_env(monkeypatch):
    monkeypatch.setenv("SCRAPER_BASE_URL", "http://127.0.0.1:19003")
    monkeypatch.setenv("SCRAPER_API_KEY", "env-provider-key")

    settings = Settings(
        DATABASE_URL="sqlite+aiosqlite:///./dev.db",
        REDIS_URL="redis://localhost:6379/0",
        SECRET_KEY="x" * 32,
        SCRAPER_BASE_URL="",
        SCRAPER_API_KEY="",
    )

    assert settings.SCRAPER_BASE_URL == "http://127.0.0.1:19003"
    assert settings.SCRAPER_API_KEY == "env-provider-key"

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.api.deps import get_db
from app.main import create_app


pytestmark = pytest.mark.asyncio


def _override_db(session_factory):
    async def override_get_db():
        async with session_factory() as session:
            yield session

    return override_get_db


async def _register_and_login(client: AsyncClient, email: str) -> str:
    password = "Super-secret-123"
    register_response = await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": password},
    )
    assert register_response.status_code == 201

    login_response = await client.post(
        "/api/v1/auth/login",
        data={"username": email, "password": password},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    assert login_response.status_code == 200
    return login_response.json()["access_token"]


def _headers(*, token: str | None = None, api_key: str | None = None) -> dict[str, str]:
    headers: dict[str, str] = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    if api_key:
        headers["X-API-Key"] = api_key
    return headers


async def test_provider_credential_write_requires_authentication(test_engine):
    session_factory = async_sessionmaker(test_engine, expire_on_commit=False)
    app = create_app()
    app.dependency_overrides[get_db] = _override_db(session_factory)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.post(
            "/api/v1/credentials",
            json={"provider": "openai", "api_key": "sk-test-provider-key"},
        )

    assert response.status_code == 401
    assert response.json().get("detail") == "Could not validate credentials"


async def test_provider_credential_write_accepts_jwt_without_api_key_header(test_engine):
    session_factory = async_sessionmaker(test_engine, expire_on_commit=False)
    app = create_app()
    app.dependency_overrides[get_db] = _override_db(session_factory)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        token = await _register_and_login(client, "provider-jwt-only@example.com")
        response = await client.post(
            "/api/v1/credentials",
            headers=_headers(token=token),
            json={"provider": "openai", "api_key": "sk-test-provider-key"},
        )

    assert response.status_code == 201
    assert response.json().get("provider") == "openai"


async def test_provider_and_system_api_key_flows_support_cross_app_usage(test_engine):
    session_factory = async_sessionmaker(test_engine, expire_on_commit=False)
    app = create_app()
    app.dependency_overrides[get_db] = _override_db(session_factory)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        token = await _register_and_login(client, "provider-system-key-flow@example.com")

        provider_response = await client.post(
            "/api/v1/credentials",
            headers=_headers(token=token),
            json={"provider": "openai", "api_key": "sk-provider-openai-key"},
        )
        assert provider_response.status_code == 201
        provider_payload = provider_response.json()
        assert provider_payload["provider"] == "openai"
        assert "api_key" not in provider_payload
        assert provider_payload["key_mask"].startswith("sk-p")

        created_key_response = await client.post(
            "/api/v1/api-keys",
            headers=_headers(token=token),
            json={"name": "External App"},
        )
        assert created_key_response.status_code == 201
        created_key = created_key_response.json()["api_key"]
        assert created_key.startswith("ss_")

        # Simulate "another app" call using only API key auth (no JWT).
        cross_app_write = await client.post(
            "/api/v1/credentials",
            headers=_headers(api_key=created_key),
            json={"provider": "gemini", "api_key": "gm-provider-key"},
        )
        assert cross_app_write.status_code == 201
        assert cross_app_write.json()["provider"] == "gemini"

        cross_app_read = await client.get(
            "/api/v1/credentials",
            headers=_headers(api_key=created_key),
        )
        assert cross_app_read.status_code == 200
        providers = {item["provider"] for item in cross_app_read.json().get("credentials", [])}
        assert {"openai", "gemini"}.issubset(providers)

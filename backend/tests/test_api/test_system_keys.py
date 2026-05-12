import uuid

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.api.deps import get_db
from app.config import settings
from app.main import create_app


pytestmark = pytest.mark.asyncio
TEST_API_KEY = "test-global-api-key"


def _override_db(session_factory):
    async def override_get_db():
        async with session_factory() as session:
            yield session

    return override_get_db


def _unique_email(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:10]}@example.com"


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


def _auth_headers(token: str) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {token}",
        "X-API-Key": TEST_API_KEY,
    }


@pytest_asyncio.fixture
async def api_client(test_engine):
    session_factory = async_sessionmaker(test_engine, expire_on_commit=False)
    app = create_app()
    app.dependency_overrides[get_db] = _override_db(session_factory)
    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        yield client

    app.dependency_overrides.clear()


async def test_system_keys_crud_flow(api_client, monkeypatch):
    monkeypatch.setattr(settings, "SYSTEM_KEYS_ADMIN_EMAILS", [])
    client = api_client
    token = await _register_and_login(client, _unique_email("system-keys"))
    headers = _auth_headers(token)

    initial = await client.get("/api/v1/system-keys", headers=headers)
    assert initial.status_code == 200
    assert isinstance(initial.json().get("secrets"), list)

    saved = await client.put(
        "/api/v1/system-keys/OPENAI_API_KEY",
        headers=headers,
        json={"value": "sk-test-system-key-123"},
    )
    assert saved.status_code == 200
    saved_body = saved.json()
    assert saved_body["name"] == "OPENAI_API_KEY"
    assert saved_body["configured"] is True
    assert saved_body["source"] == "database"
    assert saved_body["key_mask"]

    listed = await client.get("/api/v1/system-keys", headers=headers)
    assert listed.status_code == 200
    openai_item = next((item for item in listed.json()["secrets"] if item["name"] == "OPENAI_API_KEY"), None)
    assert openai_item is not None
    assert openai_item["configured"] is True
    assert openai_item["source"] == "database"

    deleted = await client.delete("/api/v1/system-keys/OPENAI_API_KEY", headers=headers)
    assert deleted.status_code == 204


async def test_system_keys_admin_restriction(api_client, monkeypatch):
    admin_email = _unique_email("system-keys-admin")
    non_admin_email = _unique_email("system-keys-user")
    monkeypatch.setattr(settings, "SYSTEM_KEYS_ADMIN_EMAILS", [admin_email.lower()])

    client = api_client
    admin_token = await _register_and_login(client, admin_email)
    non_admin_token = await _register_and_login(client, non_admin_email)

    admin_list = await client.get("/api/v1/system-keys", headers=_auth_headers(admin_token))
    assert admin_list.status_code == 200

    blocked = await client.get("/api/v1/system-keys", headers=_auth_headers(non_admin_token))
    assert blocked.status_code == 403
    assert "only system-key admins" in blocked.text.lower()


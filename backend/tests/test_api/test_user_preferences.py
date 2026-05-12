from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.api.deps import get_db
from app.main import create_app

pytestmark = pytest.mark.asyncio

TEST_API_KEY = "test-global-api-key"


def _override_db(session_factory):
    async def override_get_db():
        async with session_factory() as session:
            yield session

    return override_get_db


def _auth_headers(token: str) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {token}",
        "X-API-Key": TEST_API_KEY,
    }


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


async def test_dashboard_preferences_defaults_and_updates(test_engine):
    session_factory = async_sessionmaker(test_engine, expire_on_commit=False)
    app = create_app()
    app.dependency_overrides[get_db] = _override_db(session_factory)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        email = f"prefs-{uuid4().hex[:10]}@example.com"
        token = await _register_and_login(client, email)

        default_response = await client.get(
            "/api/v1/user/preferences/dashboard",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert default_response.status_code == 200
        assert default_response.json()["preferences"]["visibility"] == "Internal Only"

        payload = {
            "visibility": "Executive Review",
            "category_filter": "Design",
            "notifications": {
                "budget_warnings": False,
                "overdue_tasks": True,
                "milestone_alerts": False,
                "executive_digest": True,
            },
            "plan_tags": ["Priority Review", "Q2 Launch"],
        }

        update_response = await client.put(
            "/api/v1/user/preferences/dashboard",
            json=payload,
            headers=_auth_headers(token),
        )
        assert update_response.status_code == 200
        assert update_response.json()["preferences"] == payload
        assert update_response.json()["updated_at"] is not None

        fetch_response = await client.get(
            "/api/v1/user/preferences/dashboard",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert fetch_response.status_code == 200
        assert fetch_response.json()["preferences"] == payload

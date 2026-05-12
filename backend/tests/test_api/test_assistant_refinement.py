import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker
from uuid import uuid4

from app.api.deps import get_db
from app.main import create_app

pytestmark = pytest.mark.asyncio
TEST_API_KEY = "test-global-api-key"


def _override_db(session_factory):
    async def override_get_db():
        async with session_factory() as session:
            yield session

    return override_get_db


async def _register_and_login(client: AsyncClient, email: str) -> str:
    password = "Super-secret-123!"
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


async def test_request_refinement_requires_authentication(test_engine):
    session_factory = async_sessionmaker(test_engine, expire_on_commit=False)
    app = create_app()
    app.dependency_overrides[get_db] = _override_db(session_factory)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.post(
            "/api/v1/assistant/request-refinement",
            json={
                "url": "https://example.com/catalog",
                "draft_prompt": "Get products",
                "user_message": "extract names and prices",
                "conversation": [],
            },
        )

    assert response.status_code == 401


async def test_request_refinement_returns_structured_response(test_engine):
    session_factory = async_sessionmaker(test_engine, expire_on_commit=False)
    app = create_app()
    app.dependency_overrides[get_db] = _override_db(session_factory)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        token = await _register_and_login(client, f"assistant-refine-{uuid4()}@example.com")
        response = await client.post(
            "/api/v1/assistant/request-refinement",
            headers=_auth_headers(token),
            json={
                "url": "https://example.com/catalog",
                "draft_prompt": "need product info",
                "user_message": "collect product title, price, and stock from all pages",
                "conversation": [],
            },
        )

    assert response.status_code == 200
    payload = response.json()
    assert "assistant_message" in payload
    assert "refined_prompt" in payload
    assert payload["recommended_scrape_type"] in {
        "general",
        "structured",
        "pdf",
        "word",
        "excel",
        "images",
        "videos",
    }
    assert isinstance(payload["ready_to_apply"], bool)

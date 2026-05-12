from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.api.deps import get_db
from app.main import create_app

pytestmark = pytest.mark.asyncio


def _unique_email(prefix: str) -> str:
    return f"{prefix}-{uuid4().hex[:12]}@example.com"


async def test_register_normalizes_email_to_lowercase(test_engine):
    session_factory = async_sessionmaker(test_engine, expire_on_commit=False)

    async def override_get_db():
        async with session_factory() as session:
            yield session

    app = create_app()
    app.dependency_overrides[get_db] = override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        email = _unique_email("mixed-case")
        mixed_case_email = email.upper()

        response = await client.post(
            "/api/v1/auth/register",
            json={"email": mixed_case_email, "password": "Super-secret-123"},
        )

        assert response.status_code == 201
        assert response.json()["email"] == email


async def test_login_accepts_case_and_whitespace_variations(test_engine):
    session_factory = async_sessionmaker(test_engine, expire_on_commit=False)

    async def override_get_db():
        async with session_factory() as session:
            yield session

    app = create_app()
    app.dependency_overrides[get_db] = override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        email = _unique_email("login-case")

        register_response = await client.post(
            "/api/v1/auth/register",
            json={"email": email, "password": "Super-secret-123"},
        )
        assert register_response.status_code == 201

        login_response = await client.post(
            "/api/v1/auth/login",
            data={"username": f"  {email.upper()}  ", "password": "Super-secret-123"},
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )

        assert login_response.status_code == 200
        body = login_response.json()
        assert body["token_type"] == "bearer"
        assert isinstance(body["access_token"], str) and body["access_token"]


async def test_register_rejects_weak_password_without_uppercase(test_engine):
    session_factory = async_sessionmaker(test_engine, expire_on_commit=False)

    async def override_get_db():
        async with session_factory() as session:
            yield session

    app = create_app()
    app.dependency_overrides[get_db] = override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.post(
            "/api/v1/auth/register",
            json={"email": _unique_email("weak-pass"), "password": "lowercase-123"},
        )

        assert response.status_code == 400
        assert "uppercase" in response.json()["detail"].lower()


async def test_login_invalid_credentials_message_is_consistent(test_engine):
    session_factory = async_sessionmaker(test_engine, expire_on_commit=False)

    async def override_get_db():
        async with session_factory() as session:
            yield session

    app = create_app()
    app.dependency_overrides[get_db] = override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        email = _unique_email("consistency")
        register_response = await client.post(
            "/api/v1/auth/register",
            json={"email": email, "password": "Super-secret-123"},
        )
        assert register_response.status_code == 201

        existing_user_response = await client.post(
            "/api/v1/auth/login",
            data={"username": email, "password": "wrong-password"},
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        missing_user_response = await client.post(
            "/api/v1/auth/login",
            data={"username": _unique_email("missing-user"), "password": "wrong-password"},
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )

        assert existing_user_response.status_code == 401
        assert missing_user_response.status_code == 401
        assert existing_user_response.json()["detail"] == "Incorrect email or password"
        assert missing_user_response.json()["detail"] == "Incorrect email or password"

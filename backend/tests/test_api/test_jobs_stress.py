import uuid

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.api.deps import get_db
from app.main import create_app
from app.models.job import Job
from app.models.run import Run


pytestmark = pytest.mark.asyncio


def _override_db(session_factory):
    async def override_get_db():
        async with session_factory() as session:
            yield session

    return override_get_db


def _unique_email(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:10]}@example.com"


async def _register_and_login(client: AsyncClient, email: str) -> str:
    password = "super-secret-123"
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


@pytest_asyncio.fixture
async def api_client(test_engine):
    session_factory = async_sessionmaker(test_engine, expire_on_commit=False)
    app = create_app()
    app.dependency_overrides[get_db] = _override_db(session_factory)
    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        yield client, session_factory

    app.dependency_overrides.clear()


async def test_create_job_happy_path_returns_201_and_persists(api_client):
    client, session_factory = api_client
    token = await _register_and_login(client, _unique_email("jobs-happy"))
    headers = {"Authorization": f"Bearer {token}"}

    payload = {
        "url": "https://example.com/catalog",
        "scrape_type": "general",
        "prompt": "Extract product names and prices.",
        "max_pages": 5,
        "follow_pagination": True,
        "config": {
            "timeout_ms": 30_000,
            "wait_until": "domcontentloaded",
            "rate_limit_delay": 0.5,
        },
    }
    response = await client.post("/api/v1/jobs", headers=headers, json=payload)

    assert response.status_code == 201
    body = response.json()
    assert body["id"]
    assert body["status"] == "pending"
    assert body["url"].startswith("https://example.com/catalog")
    assert body["max_pages"] == 5

    async with session_factory() as session:
        stmt = select(Job).where(Job.id == uuid.UUID(body["id"]))
        persisted = (await session.execute(stmt)).scalar_one_or_none()

    assert persisted is not None
    assert persisted.user_id is not None
    assert persisted.scrape_type == "general"
    assert persisted.config["max_pages"] == 5
    assert persisted.config["follow_pagination"] is True


@pytest.mark.parametrize(
    ("case_name", "payload", "error_hint"),
    [
        (
            "unknown_config_key",
            {
                "url": "https://example.com/catalog",
                "scrape_type": "general",
                "config": {"unknown_key": "boom"},
            },
            "extra",
        ),
        (
            "max_pages_out_of_bounds",
            {
                "url": "https://example.com/catalog",
                "scrape_type": "general",
                "max_pages": 10_000,
            },
            "max_pages",
        ),
        (
            "invalid_timeout_ms",
            {
                "url": "https://example.com/catalog",
                "scrape_type": "general",
                "config": {"timeout_ms": -50},
            },
            "timeout_ms",
        ),
    ],
)
async def test_create_job_strict_schema_rejections_return_422(api_client, case_name, payload, error_hint):
    client, _ = api_client
    token = await _register_and_login(client, _unique_email(f"jobs-422-{case_name}"))
    headers = {"Authorization": f"Bearer {token}"}

    response = await client.post("/api/v1/jobs", headers=headers, json=payload)

    assert response.status_code == 422, response.text
    assert error_hint.lower() in response.text.lower()


async def test_create_job_missing_url_returns_422(api_client):
    client, _ = api_client
    token = await _register_and_login(client, _unique_email("jobs-missing-url"))
    headers = {"Authorization": f"Bearer {token}"}

    response = await client.post(
        "/api/v1/jobs",
        headers=headers,
        json={
            "scrape_type": "general",
            "max_pages": 1,
        },
    )

    assert response.status_code == 422
    assert "url" in response.text.lower()


@pytest.mark.parametrize("active_status", ["pending", "running"])
async def test_create_job_run_returns_409_when_active_run_exists(api_client, active_status):
    client, session_factory = api_client
    token = await _register_and_login(client, _unique_email(f"jobs-active-{active_status}"))
    headers = {"Authorization": f"Bearer {token}"}

    create_job_response = await client.post(
        "/api/v1/jobs",
        headers=headers,
        json={
            "url": "https://example.com/listing",
            "scrape_type": "general",
            "max_pages": 2,
        },
    )
    assert create_job_response.status_code == 201
    job_id = create_job_response.json()["id"]

    async with session_factory() as session:
        session.add(
            Run(
                job_id=uuid.UUID(job_id),
                status=active_status,
                progress=10 if active_status == "running" else 0,
            )
        )
        await session.commit()

    run_response = await client.post(f"/api/v1/jobs/{job_id}/runs", headers=headers)
    assert run_response.status_code == 409
    assert "already pending or running" in run_response.text.lower()

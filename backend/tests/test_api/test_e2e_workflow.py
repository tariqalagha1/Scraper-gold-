import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.api.deps import get_db
from app.api.v1 import exports as exports_api
from app.api.v1 import jobs as jobs_api
from app.main import create_app
from app.queue import tasks

pytestmark = pytest.mark.asyncio


class _DelayRecorder:
    def __init__(self) -> None:
        self.calls: list[tuple[str, ...]] = []

    def delay(self, *args: str) -> None:
        self.calls.append(tuple(args))


async def test_register_to_export_download_workflow(
    test_engine,
    isolated_storage,
    sample_site,
    monkeypatch,
):
    session_factory = async_sessionmaker(test_engine, expire_on_commit=False)
    monkeypatch.setattr(tasks, "async_session_factory", session_factory)

    async def override_get_db():
        async with session_factory() as session:
            yield session

    run_delay = _DelayRecorder()
    export_delay = _DelayRecorder()
    monkeypatch.setattr(jobs_api, "run_scraping_job", run_delay)
    monkeypatch.setattr(exports_api, "run_export", export_delay)

    app = create_app()
    app.dependency_overrides[get_db] = override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        register_response = await client.post(
            "/api/v1/auth/register",
            json={"email": "e2e@example.com", "password": "super-secret-123"},
        )
        assert register_response.status_code == 201

        login_response = await client.post(
            "/api/v1/auth/login",
            data={"username": "e2e@example.com", "password": "super-secret-123"},
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        assert login_response.status_code == 200
        token = login_response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        job_response = await client.post(
            "/api/v1/jobs",
            headers=headers,
            json={
                "url": sample_site["page_url"],
                "prompt": "Capture the table and downloadable report",
                "scrape_type": "general",
                "max_pages": 1,
                "follow_pagination": False,
            },
        )
        assert job_response.status_code == 201
        job_id = job_response.json()["id"]

        run_response = await client.post(f"/api/v1/jobs/{job_id}/runs", headers=headers)
        assert run_response.status_code == 201
        run_id = run_response.json()["id"]
        assert run_delay.calls == [(job_id, register_response.json()["id"], run_id)]

        execution = await tasks._execute_scraping_job(job_id, register_response.json()["id"], run_id)
        assert execution["status"] == "completed"

        persisted_run = await client.get(f"/api/v1/runs/{run_id}", headers=headers)
        assert persisted_run.status_code == 200
        assert persisted_run.json()["status"] == "completed"

        export_response = await client.post(
            "/api/v1/exports",
            headers=headers,
            json={"run_id": run_id, "format": "pdf"},
        )
        assert export_response.status_code == 201
        export_id = export_response.json()["id"]
        assert export_delay.calls == [(export_id, register_response.json()["id"])]

        export_execution = await tasks._execute_export(export_id, register_response.json()["id"])
        assert export_execution["status"] == "completed"

        download_response = await client.get(f"/api/v1/exports/{export_id}/download", headers=headers)
        assert download_response.status_code == 200
        assert download_response.headers["content-type"].startswith("application/pdf")
        assert len(download_response.content) > 0

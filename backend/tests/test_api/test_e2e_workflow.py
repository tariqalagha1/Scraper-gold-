import asyncio
from uuid import UUID

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.api.deps import get_db
from app.api.v1 import jobs as jobs_api
from app.main import create_app
from app.models.job import Job
from app.models.result import Result
from app.models.run import Run

pytestmark = pytest.mark.asyncio
TEST_API_KEY = "test-global-api-key"


async def test_register_to_export_download_workflow(
    test_engine,
    isolated_storage,
    sample_site,
    monkeypatch,
):
    session_factory = async_sessionmaker(test_engine, expire_on_commit=False)
    monkeypatch.setattr("app.execution.export_execution_service.async_session_factory", session_factory)

    async def override_get_db():
        async with session_factory() as session:
            yield session

    async def fake_execute_scraping_run(job_id: str, user_id: str | None = None, payload: dict | None = None, trace_id: str | None = None):
        run_id = str((payload or {}).get("run_id") or "")
        async with session_factory() as session:
            db_job = (await session.execute(select(Job).where(Job.id == UUID(job_id)))).scalar_one()
            db_run = (await session.execute(select(Run).where(Run.id == UUID(run_id)))).scalar_one()
            db_run.status = "completed"
            db_run.progress = 100
            db_job.status = "completed"
            session.add(
                Result(
                    run_id=db_run.id,
                    data_json={"status": "completed", "processed_data": {"items": [{"name": "Alpha"}]}, "errors": []},
                    data_type=db_job.scrape_type,
                    raw_html_path=None,
                    screenshot_path=None,
                    url=db_job.url,
                )
            )
            await session.commit()
        return {"status": "completed", "run_id": run_id, "job_id": job_id, "trace_id": trace_id, "errors": []}

    monkeypatch.setattr(jobs_api, "execute_scraping_run", fake_execute_scraping_run)

    app = create_app()
    app.dependency_overrides[get_db] = override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        register_response = await client.post(
            "/api/v1/auth/register",
            json={"email": "e2e@example.com", "password": "Super-secret-123"},
        )
        assert register_response.status_code == 201

        login_response = await client.post(
            "/api/v1/auth/login",
            data={"username": "e2e@example.com", "password": "Super-secret-123"},
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        assert login_response.status_code == 200
        token = login_response.json()["access_token"]
        headers = {
            "Authorization": f"Bearer {token}",
            "X-API-Key": TEST_API_KEY,
        }

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

        async with session_factory() as session:
            db_job = (await session.execute(select(Job).where(Job.id == UUID(job_id)))).scalar_one()
            db_run = (await session.execute(select(Run).where(Run.id == UUID(run_id)))).scalar_one()
            db_run.status = "completed"
            db_run.progress = 100
            db_job.status = "completed"
            session.add(
                Result(
                    run_id=db_run.id,
                    data_json={"status": "completed", "processed_data": {"items": [{"name": "Alpha"}]}, "errors": []},
                    data_type=db_job.scrape_type,
                    raw_html_path=None,
                    screenshot_path=None,
                    url=db_job.url,
                )
            )
            await session.commit()

        persisted_run = await client.get(f"/api/v1/runs/{run_id}", headers=headers)
        assert persisted_run.status_code == 200
        assert persisted_run.json()["status"] == "completed"

        export_response = await client.post(
            "/api/v1/exports",
            headers=headers,
            json={"run_id": run_id, "format": "json"},
        )
        assert export_response.status_code == 201
        export_id = export_response.json()["id"]
        assert export_response.json()["status"] in {"queued", "running", "completed"}

        final_export = export_response.json()
        for _ in range(40):
            export_status_response = await client.get(f"/api/v1/exports/{export_id}", headers=headers)
            assert export_status_response.status_code == 200
            final_export = export_status_response.json()
            if final_export["status"] == "completed" and final_export["file_path"]:
                break
            await asyncio.sleep(0.05)
        assert final_export["status"] == "completed"
        assert final_export["file_path"]

        download_response = await client.get(f"/api/v1/exports/{export_id}/download", headers=headers)
        assert download_response.status_code == 200
        assert download_response.headers["content-type"].startswith("application/json")
        assert len(download_response.content) > 0

from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.api.deps import get_db
from app.main import create_app
from app.models.export import Export
from app.models.job import Job
from app.models.result import Result
from app.models.run import Run
from app.models.user import User
from app.services import user_cleanup as user_cleanup_service
from app.storage.manager import StorageManager

pytestmark = pytest.mark.asyncio


def _override_db(session_factory):
    async def override_get_db():
        async with session_factory() as session:
            yield session

    return override_get_db


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


async def _build_user_history(session_factory, email: str, storage_root: Path) -> dict[str, object]:
    storage = StorageManager()
    async with session_factory() as session:
        user = (await session.execute(select(User).where(User.email == email))).scalar_one()
        job = Job(
            user_id=user.id,
            url="https://example.com/catalog",
            scrape_type="structured",
            config={"prompt": "Find prices"},
            status="completed",
        )
        session.add(job)
        await session.flush()

        run = Run(job_id=job.id, status="completed", progress=100)
        session.add(run)
        await session.flush()

        raw_html_path = storage.save_raw_html(run.id, job.url, "<html>test</html>")
        screenshot_path = storage.save_screenshot(run.id, job.url, b"fake-image")
        markdown_path = storage.save_markdown_snapshot(run.id, "# Snapshot")
        export_path = storage.save_export("export-test", "pdf", b"%PDF-1.4 fixture")

        result = Result(
            run_id=run.id,
            data_json={"title": "Fixture"},
            data_type="structured",
            raw_html_path=raw_html_path,
            screenshot_path=screenshot_path,
            url=job.url,
        )
        session.add(result)
        await session.flush()

        export = Export(
            run_id=run.id,
            result_id=result.id,
            format="pdf",
            file_path=export_path,
            file_size=storage.get_file_size(export_path),
        )
        session.add(export)

        run.markdown_snapshot_path = markdown_path

        run_logs_dir = storage_root / "run_logs"
        run_logs_dir.mkdir(parents=True, exist_ok=True)
        run_log_path = run_logs_dir / f"{run.id}.jsonl"
        run_log_path.write_text('{"event":"run_completed"}\n', encoding="utf-8")

        await session.commit()

        return {
            "user_id": user.id,
            "job_id": job.id,
            "run_id": run.id,
            "result_id": result.id,
            "export_id": export.id,
            "raw_html_path": raw_html_path,
            "screenshot_path": screenshot_path,
            "markdown_path": markdown_path,
            "export_path": export_path,
            "run_log_path": str(run_log_path),
        }


async def test_clear_temp_files_only_removes_owned_artifacts(test_engine, isolated_storage):
    session_factory = async_sessionmaker(test_engine, expire_on_commit=False)
    app = create_app()
    app.dependency_overrides[get_db] = _override_db(session_factory)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        token = await _register_and_login(client, "cleanup-temp@example.com")
        assets = await _build_user_history(session_factory, "cleanup-temp@example.com", isolated_storage)

        response = await client.delete(
            "/api/v1/user/temp-files",
            headers={"Authorization": f"Bearer {token}"},
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "success"
    assert payload["deleted_history_records"] == 0
    assert payload["deleted_temp_files"] >= 4
    assert payload["freed_space_mb"] >= 0

    for path in (
        assets["raw_html_path"],
        assets["screenshot_path"],
        assets["markdown_path"],
        assets["export_path"],
    ):
        assert not StorageManager().file_exists(path)

    assert not Path(assets["run_log_path"]).exists()

    async with session_factory() as session:
        job_count = await session.scalar(
            select(func.count()).select_from(Job).where(Job.user_id == assets["user_id"])
        )
        run = await session.scalar(select(Run).where(Run.id == assets["run_id"]))
        result = await session.scalar(select(Result).where(Result.id == assets["result_id"]))
        export = await session.scalar(select(Export).where(Export.id == assets["export_id"]))

    assert job_count == 1
    assert run is not None and run.markdown_snapshot_path is None
    assert result is not None and result.raw_html_path is None and result.screenshot_path is None
    assert export is not None and export.file_path == ""


async def test_clear_history_only_removes_current_user_records(test_engine, isolated_storage):
    session_factory = async_sessionmaker(test_engine, expire_on_commit=False)
    app = create_app()
    app.dependency_overrides[get_db] = _override_db(session_factory)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        token_a = await _register_and_login(client, "cleanup-a@example.com")
        await _register_and_login(client, "cleanup-b@example.com")
        assets_a = await _build_user_history(session_factory, "cleanup-a@example.com", isolated_storage)
        await _build_user_history(session_factory, "cleanup-b@example.com", isolated_storage)

        response = await client.delete(
            "/api/v1/user/history",
            headers={"Authorization": f"Bearer {token_a}"},
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "success"
    assert payload["deleted_history_records"] >= 4

    async with session_factory() as session:
        user_a = await session.scalar(select(User).where(User.email == "cleanup-a@example.com"))
        user_b = await session.scalar(select(User).where(User.email == "cleanup-b@example.com"))
        user_a_jobs = (
            await session.execute(select(Job).where(Job.user_id == user_a.id))
        ).scalars().all()
        user_b_jobs = (
            await session.execute(select(Job).where(Job.user_id == user_b.id))
        ).scalars().all()

    assert user_a is not None and user_b is not None
    assert len(user_a_jobs) == 0
    assert len(user_b_jobs) >= 1
    assert not Path(assets_a["run_log_path"]).exists()


async def test_clear_all_requires_auth_and_missing_files_do_not_break_cleanup(test_engine, isolated_storage):
    session_factory = async_sessionmaker(test_engine, expire_on_commit=False)
    app = create_app()
    app.dependency_overrides[get_db] = _override_db(session_factory)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        unauthorized = await client.delete("/api/v1/user/clear-all")
        assert unauthorized.status_code == 401

        token = await _register_and_login(client, "cleanup-all@example.com")
        assets = await _build_user_history(session_factory, "cleanup-all@example.com", isolated_storage)
        StorageManager().delete_file(assets["export_path"])

        response = await client.delete(
            "/api/v1/user/clear-all",
            headers={"Authorization": f"Bearer {token}"},
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "success"
    assert "history" in payload["cleared_scopes"]
    assert "temp_files" in payload["cleared_scopes"]

    async with session_factory() as session:
        user = await session.scalar(select(User).where(User.email == "cleanup-all@example.com"))
        remaining_jobs = await session.scalar(
            select(func.count()).select_from(Job).where(Job.user_id == user.id)
        )
        remaining_runs = await session.scalar(
            select(func.count()).select_from(Run).join(Job).where(Job.user_id == user.id)
        )
        remaining_results = await session.scalar(
            select(func.count()).select_from(Result).join(Run).join(Job).where(Job.user_id == user.id)
        )
        remaining_exports = await session.scalar(
            select(func.count()).select_from(Export).join(Run).join(Job).where(Job.user_id == user.id)
        )

    assert remaining_jobs == 0
    assert remaining_runs == 0
    assert remaining_results == 0
    assert remaining_exports == 0


async def test_clear_all_returns_partial_success_and_rolls_back_db_on_file_cleanup_warning(
    test_engine,
    isolated_storage,
    monkeypatch,
):
    session_factory = async_sessionmaker(test_engine, expire_on_commit=False)
    app = create_app()
    app.dependency_overrides[get_db] = _override_db(session_factory)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        token = await _register_and_login(client, "cleanup-partial@example.com")
        await _build_user_history(session_factory, "cleanup-partial@example.com", isolated_storage)

        monkeypatch.setattr(
            user_cleanup_service,
            "_cleanup_files",
            lambda artifacts: (1, 1024, ["Could not delete snapshot.md: permission denied"]),
        )

        response = await client.delete(
            "/api/v1/user/clear-all",
            headers={"Authorization": f"Bearer {token}"},
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "partial_success"
    assert payload["deleted_history_records"] == 0
    assert payload["deleted_temp_files"] == 1
    assert payload["warnings"] == ["Could not delete snapshot.md: permission denied"]

    async with session_factory() as session:
        user = await session.scalar(select(User).where(User.email == "cleanup-partial@example.com"))
        remaining_jobs = await session.scalar(
            select(func.count()).select_from(Job).where(Job.user_id == user.id)
        )
        remaining_runs = await session.scalar(
            select(func.count()).select_from(Run).join(Job).where(Job.user_id == user.id)
        )
        remaining_results = await session.scalar(
            select(func.count()).select_from(Result).join(Run).join(Job).where(Job.user_id == user.id)
        )
        remaining_exports = await session.scalar(
            select(func.count()).select_from(Export).join(Run).join(Job).where(Job.user_id == user.id)
        )

    assert remaining_jobs == 1
    assert remaining_runs == 1
    assert remaining_results == 1
    assert remaining_exports == 1

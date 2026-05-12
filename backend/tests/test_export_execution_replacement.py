import asyncio

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.api.v1.exports import create_export, get_export
from app.execution.export_execution_service import execute_export
from app.execution.export_task_registry import EXPORT_TASKS, get_export_task, register_export_task
from app.models.export import Export
from app.models.job import Job
from app.models.result import Result
from app.models.run import Run
from app.models.user import User
from app.observability.event_emitter import EVENT_BUFFER
from app.schemas.export import ExportCreate
from app.storage.manager import StorageManager

pytestmark = pytest.mark.asyncio


@pytest.fixture(autouse=True)
def _clear_export_runtime_state():
    EXPORT_TASKS.clear()
    EVENT_BUFFER.clear()
    yield
    EXPORT_TASKS.clear()
    EVENT_BUFFER.clear()


def _wire_export_execution_session_factory(db_session, monkeypatch) -> None:
    session_factory = async_sessionmaker(db_session.bind, expire_on_commit=False)
    monkeypatch.setattr("app.execution.export_execution_service.async_session_factory", session_factory)


async def _seed_user_job_run(
    db_session,
    *,
    email: str,
    run_status: str = "completed",
) -> tuple[User, Job, Run]:
    user = User(email=email, hashed_password="hashed", is_active=True)
    db_session.add(user)
    await db_session.flush()
    job = Job(
        user_id=user.id,
        url="https://example.com/source",
        scrape_type="general",
        config={},
        status=run_status,
    )
    db_session.add(job)
    await db_session.flush()
    run = Run(job_id=job.id, status=run_status, progress=100 if run_status == "completed" else 0)
    db_session.add(run)
    await db_session.commit()
    await db_session.refresh(run)
    return user, job, run


async def _seed_result_for_run(db_session, run: Run) -> Result:
    result = Result(
        run_id=run.id,
        data_json={"status": "completed", "processed_data": {"items": [{"name": "A"}]}, "errors": []},
        data_type="general",
        raw_html_path=None,
        screenshot_path=None,
        url="https://example.com/source",
    )
    db_session.add(result)
    await db_session.commit()
    await db_session.refresh(result)
    return result


async def test_export_creation_queues_direct_runtime_task(db_session, isolated_storage, monkeypatch):
    _wire_export_execution_session_factory(db_session, monkeypatch)
    storage = StorageManager()
    user, _job, run = await _seed_user_job_run(db_session, email="export-no-legacy-queue@example.com")
    await _seed_result_for_run(db_session, run)

    async def fake_execute_export(*_args, **_kwargs):
        await asyncio.sleep(0.05)
        return {"status": "completed"}

    monkeypatch.setattr("app.api.v1.exports.execute_export", fake_execute_export)

    response = await create_export(
        export_data=ExportCreate(run_id=run.id, format="json"),
        db=db_session,
        current_user=user,
        api_key="test-global-api-key",
        storage=storage,
    )

    assert response.status == "queued"


async def test_export_returns_export_id_and_trace_id(db_session, isolated_storage, monkeypatch):
    _wire_export_execution_session_factory(db_session, monkeypatch)
    storage = StorageManager()
    user, _job, run = await _seed_user_job_run(db_session, email="export-trace@example.com")
    await _seed_result_for_run(db_session, run)

    async def fake_execute_export(*_args, **_kwargs):
        await asyncio.sleep(0.05)
        return {"status": "completed"}

    monkeypatch.setattr("app.api.v1.exports.execute_export", fake_execute_export)

    response = await create_export(
        export_data=ExportCreate(run_id=run.id, format="json"),
        db=db_session,
        current_user=user,
        api_key="test-global-api-key",
        storage=storage,
    )

    assert response.id
    assert response.trace_id
    assert response.status == "queued"


async def test_export_execution_completes_successfully(db_session, monkeypatch):
    _wire_export_execution_session_factory(db_session, monkeypatch)
    user, _job, run = await _seed_user_job_run(db_session, email="export-success@example.com")
    await _seed_result_for_run(db_session, run)

    export = Export(run_id=run.id, format="json", file_path="")
    db_session.add(export)
    await db_session.commit()
    await db_session.refresh(export)

    register_export_task(export_id=str(export.id), run_id=str(run.id), trace_id="trace-export-success")
    result = await execute_export(str(export.id), str(run.id), trace_id="trace-export-success")

    await db_session.refresh(export)
    assert result["status"] == "completed"
    assert export.file_path
    assert export.file_size


async def test_export_status_updates_correctly(db_session, isolated_storage, monkeypatch):
    _wire_export_execution_session_factory(db_session, monkeypatch)
    storage = StorageManager()
    user, _job, run = await _seed_user_job_run(db_session, email="export-status@example.com")
    await _seed_result_for_run(db_session, run)

    async def fake_execute_export(export_id: str, run_id: str, trace_id: str | None = None):
        await asyncio.sleep(0.05)
        return {"status": "completed", "export_id": export_id, "run_id": run_id, "trace_id": trace_id}

    monkeypatch.setattr("app.api.v1.exports.execute_export", fake_execute_export)

    create_response = await create_export(
        export_data=ExportCreate(run_id=run.id, format="json"),
        db=db_session,
        current_user=user,
        api_key="test-global-api-key",
        storage=storage,
    )
    assert create_response.status == "queued"

    export_response = await get_export(create_response.id, db_session, user)
    assert export_response.status in {"queued", "running", "completed"}
    assert export_response.trace_id


async def test_export_failure_handled(db_session, monkeypatch):
    _wire_export_execution_session_factory(db_session, monkeypatch)
    _user, _job, run = await _seed_user_job_run(db_session, email="export-failure@example.com")

    export = Export(run_id=run.id, format="json", file_path="")
    db_session.add(export)
    await db_session.commit()
    await db_session.refresh(export)

    register_export_task(export_id=str(export.id), run_id=str(run.id), trace_id="trace-export-failed")
    result = await execute_export(str(export.id), str(run.id), trace_id="trace-export-failed")
    state = get_export_task(str(export.id))

    assert result["status"] == "failed"
    assert state is not None
    assert state["status"] == "failed"
    assert state["error"]


async def test_export_events_emitted(db_session, monkeypatch):
    _wire_export_execution_session_factory(db_session, monkeypatch)
    _user, _job, run = await _seed_user_job_run(db_session, email="export-events@example.com")
    await _seed_result_for_run(db_session, run)

    export = Export(run_id=run.id, format="json", file_path="")
    db_session.add(export)
    await db_session.commit()
    await db_session.refresh(export)

    register_export_task(export_id=str(export.id), run_id=str(run.id), trace_id="trace-export-events")
    await execute_export(str(export.id), str(run.id), trace_id="trace-export-events")
    event_types = [event.get("event_type") for event in EVENT_BUFFER if event.get("trace_id") == "trace-export-events"]

    assert "EXPORT_STARTED" in event_types
    assert "EXPORT_COMPLETED" in event_types

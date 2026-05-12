import asyncio

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.api.v1.jobs import create_job_run
from app.control.control_service import set_control
from app.execution.brainit_execution_service import execute_scraping_run
from app.execution.task_registry import RUNNING_TASKS, register_task
from app.models.job import Job
from app.models.result import Result
from app.models.run import Run
from app.models.user import User
from app.observability.event_emitter import get_latest_events
from app.schemas.execution_contract import build_execution_contract_from_job_config
from app.services.run_logs import read_run_logs

pytestmark = pytest.mark.asyncio


@pytest.fixture(autouse=True)
def _clear_runtime_state():
    RUNNING_TASKS.clear()
    yield
    RUNNING_TASKS.clear()


async def _seed_user_and_job(db_session, *, email: str) -> tuple[User, Job]:
    user = User(email=email, hashed_password="hashed", is_active=True)
    db_session.add(user)
    await db_session.flush()
    job = Job(
        user_id=user.id,
        url="https://example.com/start",
        scrape_type="general",
        config={"query": "restaurants", "location": "riyadh", "fields": ["name", "phone"]},
        status="pending",
    )
    db_session.add(job)
    await db_session.commit()
    await db_session.refresh(job)
    return user, job


def _wire_execution_session_factory(db_session, monkeypatch) -> None:
    session_factory = async_sessionmaker(db_session.bind, expire_on_commit=False)
    monkeypatch.setattr("app.execution.brainit_execution_service.async_session_factory", session_factory)


async def test_job_run_uses_direct_runtime_scheduler(db_session, monkeypatch):
    _wire_execution_session_factory(db_session, monkeypatch)

    async def fake_execute(*_args, **_kwargs):
        return {"status": "completed", "errors": []}

    monkeypatch.setattr("app.api.v1.jobs.execute_scraping_run", fake_execute)
    user, job = await _seed_user_and_job(db_session, email="brainit-no-delay@example.com")

    response = await create_job_run(job.id, db_session, user)

    assert response.status == "queued"


async def test_job_run_returns_run_id_and_trace_id(db_session, monkeypatch):
    _wire_execution_session_factory(db_session, monkeypatch)

    async def fake_execute(*_args, **_kwargs):
        return {"status": "completed", "errors": []}

    monkeypatch.setattr("app.api.v1.jobs.execute_scraping_run", fake_execute)
    user, job = await _seed_user_and_job(db_session, email="brainit-run-response@example.com")

    response = await create_job_run(job.id, db_session, user)

    assert response.run_id
    assert response.trace_id
    assert response.status == "queued"


async def test_brainit_execution_updates_run_status(db_session, monkeypatch):
    _wire_execution_session_factory(db_session, monkeypatch)
    user, job = await _seed_user_and_job(db_session, email="brainit-status@example.com")
    run = Run(job_id=job.id, status="pending", progress=0)
    db_session.add(run)
    await db_session.commit()
    await db_session.refresh(run)

    async def fake_multi(_request, _trace_id, _execution_controls=None):
        return {
            "final_data": [{"name": "A", "phone": "111"}],
            "errors": [],
            "sources_used": ["internal"],
            "sources_skipped": [],
            "execution_order": ["internal"],
            "cross_source_duplicates_removed": 0,
            "execution_tiers": {"high": ["internal"], "medium": [], "low": []},
            "tiers_executed": ["high"],
            "early_stopped": False,
            "fallback_used": False,
            "retries_triggered": [],
        }

    monkeypatch.setattr("app.execution.brainit_execution_service._execute_multi_source", fake_multi)
    register_task(run_id=str(run.id), job_id=str(job.id), trace_id="trace-status")

    result = await execute_scraping_run(
        str(job.id),
        user_id=str(user.id),
        payload={"run_id": str(run.id)},
        trace_id="trace-status",
    )

    await db_session.refresh(run)
    db_result = (await db_session.execute(select(Result).where(Result.run_id == run.id))).scalar_one_or_none()

    assert result["status"] in {"completed", "partial"}
    assert run.status == "completed"
    assert db_result is not None
    assert db_result.data_json["execution"]["validation"]["confidence"] >= 0


async def test_control_cancel_affects_running_execution(db_session, monkeypatch):
    _wire_execution_session_factory(db_session, monkeypatch)
    user, job = await _seed_user_and_job(db_session, email="brainit-cancel@example.com")
    run = Run(job_id=job.id, status="pending", progress=0)
    db_session.add(run)
    await db_session.commit()
    await db_session.refresh(run)

    async def fake_multi(_request, trace_id, _execution_controls=None):
        await asyncio.sleep(0.05)
        set_control(trace_id, "cancel", True)
        raise RuntimeError("cancelled")

    monkeypatch.setattr("app.execution.brainit_execution_service._execute_multi_source", fake_multi)
    register_task(run_id=str(run.id), job_id=str(job.id), trace_id="trace-cancel")

    result = await execute_scraping_run(
        str(job.id),
        user_id=str(user.id),
        payload={"run_id": str(run.id)},
        trace_id="trace-cancel",
    )
    await db_session.refresh(run)

    assert result["status"] == "failed"
    assert run.status == "failed"


async def test_events_visible_from_brainit_execution(db_session, monkeypatch):
    _wire_execution_session_factory(db_session, monkeypatch)
    user, job = await _seed_user_and_job(db_session, email="brainit-events@example.com")
    run = Run(job_id=job.id, status="pending", progress=0)
    db_session.add(run)
    await db_session.commit()
    await db_session.refresh(run)

    async def fake_multi(_request, _trace_id, _execution_controls=None):
        return {
            "final_data": [{"name": "A"}],
            "errors": [],
            "sources_used": ["internal"],
            "sources_skipped": [],
            "execution_order": ["internal"],
            "cross_source_duplicates_removed": 0,
            "execution_tiers": {"high": ["internal"], "medium": [], "low": []},
            "tiers_executed": ["high"],
            "early_stopped": True,
            "fallback_used": False,
            "retries_triggered": [],
        }

    monkeypatch.setattr("app.execution.brainit_execution_service._execute_multi_source", fake_multi)
    register_task(run_id=str(run.id), job_id=str(job.id), trace_id="trace-events")

    await execute_scraping_run(
        str(job.id),
        user_id=str(user.id),
        payload={"run_id": str(run.id)},
        trace_id="trace-events",
    )
    latest = get_latest_events()
    event_types = [event.get("event_type") for event in latest if event.get("trace_id") == "trace-events"]

    assert "SCRAPE_STARTED" in event_types
    assert "SCRAPE_COMPLETED" in event_types


async def test_failed_execution_does_not_emit_completion_steps_after_failure(db_session, monkeypatch):
    _wire_execution_session_factory(db_session, monkeypatch)
    user, job = await _seed_user_and_job(db_session, email="brainit-failure-logs@example.com")
    run = Run(job_id=job.id, status="pending", progress=0)
    db_session.add(run)
    await db_session.commit()
    await db_session.refresh(run)

    async def fake_multi(_request, _trace_id, _execution_controls=None):
        return {
            "final_data": [],
            "errors": ["Cannot reach Smart Scraper service."],
            "sources_used": [],
            "sources_skipped": ["internal"],
            "execution_order": ["internal"],
            "cross_source_duplicates_removed": 0,
            "execution_tiers": {"high": ["internal"], "medium": [], "low": []},
            "tiers_executed": ["high"],
            "early_stopped": False,
            "fallback_used": False,
            "retries_triggered": [],
        }

    monkeypatch.setattr("app.execution.brainit_execution_service._execute_multi_source", fake_multi)
    register_task(run_id=str(run.id), job_id=str(job.id), trace_id="trace-failure-logs")

    result = await execute_scraping_run(
        str(job.id),
        user_id=str(user.id),
        payload={"run_id": str(run.id)},
        trace_id="trace-failure-logs",
    )

    logs = read_run_logs(str(run.id))

    assert result["status"] == "failed"
    assert logs[-1]["event"] == "run_failed"
    assert not any(
        entry["event"] == "node_completed"
        and entry.get("details", {}).get("stage") in {"event_emitter", "control_service"}
        for entry in logs
    )


async def test_policy_applies_to_brainit_execution(db_session, monkeypatch):
    _wire_execution_session_factory(db_session, monkeypatch)
    user, job = await _seed_user_and_job(db_session, email="brainit-policy@example.com")
    run = Run(job_id=job.id, status="pending", progress=0)
    db_session.add(run)
    await db_session.commit()
    await db_session.refresh(run)

    observed = {"called": False}

    def fake_enforce(*_args, **_kwargs):
        observed["called"] = True
        return {"tenant_id": "default"}, ["internal"], 10, False

    async def fake_multi(_request, _trace_id, _execution_controls=None):
        return {
            "final_data": [{"name": "A"}],
            "errors": [],
            "sources_used": ["internal"],
            "sources_skipped": [],
            "execution_order": ["internal"],
            "cross_source_duplicates_removed": 0,
            "execution_tiers": {"high": ["internal"], "medium": [], "low": []},
            "tiers_executed": ["high"],
            "early_stopped": False,
            "fallback_used": False,
            "retries_triggered": [],
        }

    monkeypatch.setattr("app.execution.brainit_execution_service.enforce_request_policy", fake_enforce)
    monkeypatch.setattr("app.execution.brainit_execution_service._execute_multi_source", fake_multi)
    register_task(run_id=str(run.id), job_id=str(job.id), trace_id="trace-policy")

    await execute_scraping_run(
        str(job.id),
        user_id=str(user.id),
        payload={"run_id": str(run.id)},
        trace_id="trace-policy",
    )

    assert observed["called"] is True


async def test_failed_execution_returns_failed_status(db_session, monkeypatch):
    _wire_execution_session_factory(db_session, monkeypatch)
    user, job = await _seed_user_and_job(db_session, email="brainit-failed@example.com")
    run = Run(job_id=job.id, status="pending", progress=0)
    db_session.add(run)
    await db_session.commit()
    await db_session.refresh(run)

    async def fake_multi(_request, _trace_id, _execution_controls=None):
        raise RuntimeError("boom")

    monkeypatch.setattr("app.execution.brainit_execution_service._execute_multi_source", fake_multi)
    register_task(run_id=str(run.id), job_id=str(job.id), trace_id="trace-failed")

    result = await execute_scraping_run(
        str(job.id),
        user_id=str(user.id),
        payload={"run_id": str(run.id)},
        trace_id="trace-failed",
    )
    await db_session.refresh(run)

    assert result["status"] == "failed"
    assert run.status == "failed"


async def test_url_backed_jobs_default_to_web_source_only():
    contract = build_execution_contract_from_job_config(
        {"query": "patient records"},
        job_url="https://example.com/patients",
    )

    assert contract.execution_mode == "single_source"
    assert contract.sources == ["web"]


async def test_job_run_defaults_url_backed_jobs_to_web_source_only(db_session, monkeypatch):
    _wire_execution_session_factory(db_session, monkeypatch)

    async def fake_execute(*_args, **_kwargs):
        return {"status": "completed", "errors": []}

    monkeypatch.setattr("app.api.v1.jobs.execute_scraping_run", fake_execute)
    user, job = await _seed_user_and_job(db_session, email="brainit-web-only@example.com")

    response = await create_job_run(job.id, db_session, user)
    run = await db_session.get(Run, response.run_id)

    assert run is not None
    assert run.execution_contract["sources"] == ["web"]
    assert run.execution_contract["execution_mode"] == "single_source"

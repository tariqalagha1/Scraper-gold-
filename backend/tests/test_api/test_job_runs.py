import pytest
from fastapi import HTTPException

from app.api.v1.jobs import create_job_run, list_job_runs
from app.api.v1.runs import get_run_logs, retry_run
from app.models.job import Job
from app.models.run import Run
from app.models.user import User
from app.services.run_logs import append_run_log

pytestmark = pytest.mark.asyncio


async def test_create_job_run_creates_pending_run_and_enqueues_task(db_session, monkeypatch):
    queued = {}

    class DelayStub:
        @staticmethod
        def delay(job_id, user_id, run_id):
            queued["job_id"] = job_id
            queued["user_id"] = user_id
            queued["run_id"] = run_id

    monkeypatch.setattr("app.api.v1.jobs.run_scraping_job", DelayStub)

    user = User(email="route-runs@example.com", hashed_password="hashed", is_active=True)
    db_session.add(user)
    await db_session.flush()
    job = Job(
        user_id=user.id,
        url="https://example.com/start",
        scrape_type="general",
        config={},
        status="pending",
    )
    db_session.add(job)
    await db_session.commit()
    await db_session.refresh(job)

    run = await create_job_run(job.id, db_session, user)

    assert run.job_id == job.id
    assert run.status == "pending"
    assert run.progress == 0
    assert run.started_at is None
    assert run.finished_at is None
    assert run.error_message is None
    assert queued == {
        "job_id": str(job.id),
        "user_id": str(user.id),
        "run_id": str(run.id),
    }


async def test_create_job_run_returns_service_unavailable_when_queue_enqueue_fails(db_session, monkeypatch):
    class DelayStub:
        @staticmethod
        def delay(job_id, user_id, run_id):
            raise RuntimeError("redis down")

    monkeypatch.setattr("app.api.v1.jobs.run_scraping_job", DelayStub)

    user = User(email="route-runs-queue-down@example.com", hashed_password="hashed", is_active=True)
    db_session.add(user)
    await db_session.flush()
    job = Job(
        user_id=user.id,
        url="https://example.com/start",
        scrape_type="general",
        config={},
        status="pending",
    )
    db_session.add(job)
    await db_session.commit()
    await db_session.refresh(job)

    with pytest.raises(HTTPException) as exc_info:
        await create_job_run(job.id, db_session, user)

    assert exc_info.value.status_code == 503
    assert "queue is unavailable" in exc_info.value.detail.lower()


async def test_list_job_runs_returns_runs_for_job(db_session):
    user = User(email="route-runs-list@example.com", hashed_password="hashed", is_active=True)
    db_session.add(user)
    await db_session.flush()
    job = Job(
        user_id=user.id,
        url="https://example.com/list",
        scrape_type="general",
        config={},
        status="pending",
    )
    db_session.add(job)
    await db_session.flush()

    first_run = Run(job_id=job.id, status="pending", progress=0)
    second_run = Run(job_id=job.id, status="running", progress=55)
    db_session.add_all([first_run, second_run])
    await db_session.commit()

    response = await list_job_runs(job.id, 0, 20, db_session, user)

    assert response.total == 2
    assert len(response.runs) == 2
    assert {run.status for run in response.runs} == {"pending", "running"}
    assert {run.progress for run in response.runs} == {0, 55}


async def test_create_job_run_rejects_duplicate_active_run(db_session):
    user = User(email="duplicate-runs@example.com", hashed_password="hashed", is_active=True)
    db_session.add(user)
    await db_session.flush()
    job = Job(
        user_id=user.id,
        url="https://example.com/duplicate",
        scrape_type="general",
        config={},
        status="pending",
    )
    db_session.add(job)
    await db_session.flush()
    db_session.add(Run(job_id=job.id, status="running", progress=20))
    await db_session.commit()

    with pytest.raises(HTTPException) as exc_info:
        await create_job_run(job.id, db_session, user)

    assert exc_info.value.status_code == 409


async def test_get_run_logs_returns_structured_file_logs(db_session):
    user = User(email="run-logs@example.com", hashed_password="hashed", is_active=True)
    db_session.add(user)
    await db_session.flush()
    job = Job(
        user_id=user.id,
        url="https://example.com/logs",
        scrape_type="general",
        config={},
        status="pending",
    )
    db_session.add(job)
    await db_session.flush()
    run = Run(job_id=job.id, status="completed", progress=100)
    db_session.add(run)
    await db_session.commit()

    append_run_log(str(run.id), event="run_started", message="Run execution started.")

    response = await get_run_logs(run.id, db_session, user)

    assert response["run_id"] == str(run.id)
    assert response["logs"][0]["event"] == "run_started"


async def test_retry_run_creates_new_pending_run(db_session, monkeypatch):
    queued = {}

    class DelayStub:
        @staticmethod
        def delay(job_id, user_id, run_id):
            queued["job_id"] = job_id
            queued["user_id"] = user_id
            queued["run_id"] = run_id

    monkeypatch.setattr("app.api.v1.runs.run_scraping_job", DelayStub)

    user = User(email="retry-runs@example.com", hashed_password="hashed", is_active=True)
    db_session.add(user)
    await db_session.flush()
    job = Job(
        user_id=user.id,
        url="https://example.com/retry",
        scrape_type="general",
        config={},
        status="failed",
    )
    db_session.add(job)
    await db_session.flush()
    run = Run(job_id=job.id, status="failed", progress=100, error_message="boom")
    db_session.add(run)
    await db_session.commit()

    retried = await retry_run(run.id, db_session, user)

    assert retried.status == "pending"
    assert retried.progress == 0
    assert queued == {
        "job_id": str(job.id),
        "user_id": str(user.id),
        "run_id": str(retried.id),
    }


async def test_retry_run_returns_service_unavailable_when_queue_enqueue_fails(db_session, monkeypatch):
    class DelayStub:
        @staticmethod
        def delay(job_id, user_id, run_id):
            raise RuntimeError("redis down")

    monkeypatch.setattr("app.api.v1.runs.run_scraping_job", DelayStub)

    user = User(email="retry-runs-queue-down@example.com", hashed_password="hashed", is_active=True)
    db_session.add(user)
    await db_session.flush()
    job = Job(
        user_id=user.id,
        url="https://example.com/retry",
        scrape_type="general",
        config={},
        status="failed",
    )
    db_session.add(job)
    await db_session.flush()
    run = Run(job_id=job.id, status="failed", progress=100, error_message="boom")
    db_session.add(run)
    await db_session.commit()

    with pytest.raises(HTTPException) as exc_info:
        await retry_run(run.id, db_session, user)

    assert exc_info.value.status_code == 503
    assert "queue is unavailable" in exc_info.value.detail.lower()

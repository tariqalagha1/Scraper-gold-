import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.models.job import Job
from app.models.run import Run
from app.models.user import User
from app.queue import tasks
from app.services.run_logs import read_run_logs

pytestmark = pytest.mark.asyncio


async def test_execute_scraping_job_advances_run_logs_beyond_pipeline_started(
    test_engine,
    isolated_storage,
    sample_site,
    monkeypatch,
):
    session_factory = async_sessionmaker(test_engine, expire_on_commit=False)
    monkeypatch.setattr(tasks, "async_session_factory", session_factory)

    async with session_factory() as session:
        user = User(email="smoke-progress@example.com", hashed_password="hashed", is_active=True)
        session.add(user)
        await session.flush()
        job = Job(
            user_id=user.id,
            url=sample_site["page_url"],
            scrape_type="general",
            config={
                "respect_robots_txt": False,
                "wait_until": "domcontentloaded",
            },
            status="pending",
        )
        session.add(job)
        await session.commit()
        job_id = str(job.id)
        user_id = str(user.id)
        persisted_job_id = job.id

    execution = await tasks._execute_scraping_job(job_id, user_id)

    assert execution["status"] == "completed"

    async with session_factory() as session:
        run = (await session.execute(select(Run).where(Run.job_id == persisted_job_id))).scalars().one()

    log_events = [entry["event"] for entry in read_run_logs(str(run.id))]

    assert "pipeline_started" in log_events
    assert "node_started" in log_events
    assert "node_completed" in log_events
    assert log_events.index("node_started") > log_events.index("pipeline_started")
    assert log_events[-1] == "run_completed"


async def test_execute_scraping_job_fails_cleanly_for_dead_host(
    test_engine,
    isolated_storage,
    monkeypatch,
):
    session_factory = async_sessionmaker(test_engine, expire_on_commit=False)
    monkeypatch.setattr(tasks, "async_session_factory", session_factory)

    async with session_factory() as session:
        user = User(email="smoke-dead-host@example.com", hashed_password="hashed", is_active=True)
        session.add(user)
        await session.flush()
        job = Job(
            user_id=user.id,
            url="http://127.0.0.1:9/unreachable",
            scrape_type="general",
            config={
                "respect_robots_txt": False,
                "wait_until": "domcontentloaded",
            },
            status="pending",
        )
        session.add(job)
        await session.commit()
        job_id = str(job.id)
        user_id = str(user.id)
        persisted_job_id = job.id

    execution = await tasks._execute_scraping_job(job_id, user_id)

    assert execution["status"] == "failed"

    async with session_factory() as session:
        run = (await session.execute(select(Run).where(Run.job_id == persisted_job_id))).scalars().one()

    log_events = [entry["event"] for entry in read_run_logs(str(run.id))]

    assert "pipeline_started" in log_events
    assert "node_started" in log_events
    assert "node_failed" in log_events or "run_failed" in log_events

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.job import Job
from app.models.user import User
from app.services.run_service import create_run, get_runs_by_job

pytestmark = pytest.mark.asyncio


async def test_create_run_starts_pending_with_zero_progress(db_session: AsyncSession):
    user = User(email="runs@example.com", hashed_password="hashed", is_active=True)
    db_session.add(user)
    await db_session.flush()

    job = Job(
        user_id=user.id,
        url="https://example.com",
        scrape_type="general",
        config={},
        status="pending",
    )
    db_session.add(job)
    await db_session.commit()
    await db_session.refresh(job)

    run = await create_run(db_session, job.id)

    assert run.status == "pending"
    assert run.progress == 0
    assert run.started_at is None
    assert run.finished_at is None
    assert run.error_message is None


async def test_get_runs_by_job_returns_job_runs_including_progress(db_session: AsyncSession):
    user = User(email="jobruns@example.com", hashed_password="hashed", is_active=True)
    db_session.add(user)
    await db_session.flush()

    job = Job(
        user_id=user.id,
        url="https://example.com/job",
        scrape_type="general",
        config={},
        status="running",
    )
    db_session.add(job)
    await db_session.commit()
    await db_session.refresh(job)

    first_run = await create_run(db_session, job.id)
    second_run = await create_run(db_session, job.id)

    first_run.progress = 25
    second_run.progress = 75
    await db_session.commit()

    runs = await get_runs_by_job(db_session, job.id, user.id)

    assert len(runs) == 2
    assert {run.progress for run in runs} == {25, 75}

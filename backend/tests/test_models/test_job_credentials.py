import pytest
from sqlalchemy import Text, cast, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.secrets import is_encrypted_secret
from app.models.job import Job
from app.models.user import User


pytestmark = pytest.mark.asyncio


async def test_job_login_credentials_are_encrypted_at_rest(db_session: AsyncSession):
    user = User(email="job-creds@example.com", hashed_password="hashed", is_active=True)
    db_session.add(user)
    await db_session.flush()

    job = Job(
        user_id=user.id,
        url="https://example.com/private",
        login_url="https://example.com/login",
        login_username="demo@example.com",
        login_password="super-secret-password",
        scrape_type="general",
        config={},
        status="pending",
    )
    db_session.add(job)
    await db_session.commit()
    await db_session.refresh(job)

    assert job.login_username == "demo@example.com"
    assert job.login_password == "super-secret-password"

    stored_username, stored_password = (
        await db_session.execute(
            select(
                cast(Job.__table__.c.login_username, Text),
                cast(Job.__table__.c.login_password, Text),
            ).where(Job.id == job.id)
        )
    ).one()

    assert stored_username != "demo@example.com"
    assert stored_password != "super-secret-password"
    assert is_encrypted_secret(stored_username)
    assert is_encrypted_secret(stored_password)

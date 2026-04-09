import pytest
from fastapi import HTTPException

from app.api.deps import get_current_user, verify_api_key
from app.api.v1.account import get_account_summary
from app.api.v1.api_keys import create_api_key, delete_api_key, list_api_keys
from app.api.v1.jobs import create_job
from app.core.security import create_access_token
from app.models.api_key import ApiKey
from app.models.export import Export
from app.models.job import Job
from app.models.result import Result
from app.models.run import Run
from app.models.user import User
from app.schemas.job import JobCreate
from app.schemas.scraping_types import ScrapingType
from app.services.saas import hash_api_key

pytestmark = pytest.mark.asyncio


async def test_api_key_crud_is_scoped_to_user(db_session):
    user = User(email="saas-owner@example.com", hashed_password="hashed", is_active=True, plan="free")
    other_user = User(email="saas-other@example.com", hashed_password="hashed", is_active=True, plan="free")
    db_session.add_all([user, other_user])
    await db_session.commit()

    created = await create_api_key(type("Payload", (), {"name": "Primary"})(), db_session, user)
    assert created.name == "Primary"
    assert created.api_key.startswith("ss_")
    assert created.key == created.api_key

    listed = await list_api_keys(0, 20, db_session, user)
    assert listed.total == 1
    assert listed.api_keys[0].name == "Primary"

    with pytest.raises(HTTPException) as exc_info:
        await delete_api_key(listed.api_keys[0].id, db_session, other_user)
    assert exc_info.value.status_code == 404


async def test_get_current_user_accepts_user_api_key(db_session):
    user = User(email="saas-auth@example.com", hashed_password="hashed", is_active=True, plan="pro")
    db_session.add(user)
    await db_session.flush()
    raw_key = "ss_test_key"
    db_session.add(ApiKey(user_id=user.id, key=hash_api_key(raw_key), name="CLI key", is_active=True))
    await db_session.commit()

    current_user = await get_current_user(None, raw_key, None, db_session)

    assert current_user.id == user.id
    assert current_user.plan == "pro"


async def test_verify_api_key_accepts_valid_jwt_without_api_key(db_session):
    user = User(email="saas-jwt-verify@example.com", hashed_password="hashed", is_active=True, plan="pro")
    db_session.add(user)
    await db_session.commit()

    token = create_access_token({"sub": str(user.id), "email": user.email})

    validated = await verify_api_key(token=token, x_api_key=None, configured_header_key=None, db=db_session)

    assert validated is None


async def test_create_job_enforces_plan_max_jobs(db_session):
    user = User(email="saas-free@example.com", hashed_password="hashed", is_active=True, plan="free")
    db_session.add(user)
    await db_session.flush()
    for index in range(5):
        db_session.add(
            Job(
                user_id=user.id,
                url=f"https://example.com/{index}",
                scrape_type="general",
                config={},
                status="pending",
            )
        )
    await db_session.commit()

    with pytest.raises(HTTPException) as exc_info:
        await create_job(
            JobCreate(url="https://example.com/overflow", scrape_type=ScrapingType.GENERAL),
            db_session,
            user,
        )

    assert exc_info.value.status_code == 403
    assert "job limit" in exc_info.value.detail.lower()


async def test_account_summary_returns_usage_counts(db_session):
    user = User(email="saas-summary@example.com", hashed_password="hashed", is_active=True, plan="pro")
    db_session.add(user)
    await db_session.flush()
    job = Job(user_id=user.id, url="https://example.com", scrape_type="general", config={}, status="completed")
    db_session.add(job)
    await db_session.flush()
    run = Run(job_id=job.id, status="completed", progress=100)
    db_session.add(run)
    await db_session.flush()
    result = Result(run_id=run.id, data_json={"summary": "ok"}, data_type="general", url="https://example.com")
    db_session.add(result)
    await db_session.flush()
    db_session.add(Export(run_id=run.id, format="pdf", file_path="exports/test.pdf", file_size=10))
    await db_session.commit()

    summary = await get_account_summary(db_session, user)

    assert summary.plan.plan == "pro"
    assert summary.usage.total_jobs == 1
    assert summary.usage.total_runs == 1
    assert summary.usage.total_exports == 1

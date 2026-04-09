import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.db import session as session_module
from app.models.user import User


pytestmark = pytest.mark.asyncio


async def test_get_db_session_requires_explicit_commit(test_engine, monkeypatch):
    factory = async_sessionmaker(
        test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    monkeypatch.setattr(session_module, "async_session_factory", factory)

    generator = session_module.get_db_session()
    session = await generator.__anext__()
    session.add(User(email="implicit-commit@example.com", hashed_password="hashed", is_active=True))
    await generator.aclose()

    async with factory() as verification_session:
        result = await verification_session.execute(
            select(User).where(User.email == "implicit-commit@example.com")
        )
        assert result.scalar_one_or_none() is None

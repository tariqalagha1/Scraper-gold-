from collections.abc import AsyncGenerator

from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine

from app.config import settings
from app.core.db import check_database_health, run_with_db_retry


def _build_engine() -> AsyncEngine:
    url = make_url(settings.DATABASE_URL)
    engine_kwargs = {
        "echo": settings.DEBUG,
        "future": True,
    }

    if not url.drivername.startswith("sqlite"):
        engine_kwargs.update(
            pool_pre_ping=True,
            pool_size=settings.DATABASE_POOL_SIZE,
            max_overflow=settings.DATABASE_MAX_OVERFLOW,
            pool_timeout=settings.DATABASE_POOL_TIMEOUT,
            pool_recycle=settings.DATABASE_POOL_RECYCLE,
            pool_use_lifo=True,
        )

    return create_async_engine(settings.DATABASE_URL, **engine_kwargs)


engine: AsyncEngine = _build_engine()

async_session_factory = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
    autocommit=False,
)


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """Yield a session without committing implicitly.

    Request handlers and service code must call ``commit()`` explicitly so
    transaction boundaries stay visible in the application layer.
    """
    async with async_session_factory() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async for session in get_db_session():
        yield session


async def init_db() -> None:
    from app import models  # noqa: F401
    from app.db.base import Base

    async def _init() -> None:
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)

    await run_with_db_retry(_init)


async def close_db() -> None:
    await engine.dispose()


async def get_db_health() -> dict[str, str]:
    return await check_database_health(engine)

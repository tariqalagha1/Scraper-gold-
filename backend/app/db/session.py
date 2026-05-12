from collections.abc import AsyncGenerator

from sqlalchemy import event, text
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
    else:
        engine_kwargs.update(
            connect_args={"timeout": 15}
        )

    return create_async_engine(settings.DATABASE_URL, **engine_kwargs)


engine: AsyncEngine = _build_engine()
_IS_SQLITE = make_url(settings.DATABASE_URL).drivername.startswith("sqlite")


if _IS_SQLITE:
    @event.listens_for(engine.sync_engine, "connect")
    def _set_sqlite_pragmas(dbapi_connection, connection_record) -> None:  # pragma: no cover
        cursor = dbapi_connection.cursor()
        # WAL + busy timeout significantly reduce "database is locked" under
        # concurrent API + worker access patterns in local development.
        cursor.execute("PRAGMA journal_mode=WAL;")
        cursor.execute("PRAGMA synchronous=NORMAL;")
        cursor.execute("PRAGMA busy_timeout=15000;")
        cursor.execute("PRAGMA foreign_keys=ON;")
        cursor.close()

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

    async def _apply_sqlite_dev_compatibility(connection) -> None:
        # Local SQLite fallbacks can survive across model changes, so add a
        # narrow compatibility shim for newly introduced run metadata columns.
        result = await connection.execute(text("PRAGMA table_info(runs)"))
        existing_columns = {str(row[1]) for row in result.fetchall()}

        compatibility_columns = {
            "execution_contract": "ALTER TABLE runs ADD COLUMN execution_contract JSON",
            "execution_result": "ALTER TABLE runs ADD COLUMN execution_result JSON",
        }
        for column_name, ddl in compatibility_columns.items():
            if column_name not in existing_columns:
                await connection.execute(text(ddl))

    async def _init() -> None:
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
            if _IS_SQLITE:
                await _apply_sqlite_dev_compatibility(connection)

    await run_with_db_retry(_init)


async def close_db() -> None:
    await engine.dispose()


async def get_db_health() -> dict[str, str]:
    return await check_database_health(engine)

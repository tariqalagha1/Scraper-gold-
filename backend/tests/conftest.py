import asyncio
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Thread
from typing import AsyncGenerator, Generator
from uuid import uuid4

import pytest
import pytest_asyncio

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

from app.db.base import Base
from app.config import settings
from app import models  # noqa: F401


# Test database URL
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="session")
async def test_engine():
    """Create test database engine."""
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    yield engine
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    
    await engine.dispose()


@pytest_asyncio.fixture
async def db_session(test_engine) -> AsyncGenerator[AsyncSession, None]:
    """Create test database session."""
    async_session_factory = async_sessionmaker(
        test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    
    async with async_session_factory() as session:
        yield session
        await session.rollback()


@pytest.fixture(autouse=True)
def disable_agent_log_persistence(monkeypatch):
    """Avoid database writes from background logging tasks during tests."""
    from app.agents.base_agent import BaseAgent

    async def _noop(*args, **kwargs):
        return None

    monkeypatch.setattr(BaseAgent, "_persist_log", _noop)


@pytest.fixture
def isolated_storage(tmp_path, monkeypatch):
    """Route storage reads and writes to a per-test temporary directory."""
    from app.storage import manager as storage_manager_module
    from app.storage import paths as storage_paths

    storage_root = tmp_path / "storage"
    raw_html_dir = storage_root / "raw_html"
    screenshots_dir = storage_root / "screenshots"
    processed_dir = storage_root / "processed"
    exports_dir = storage_root / "exports"

    monkeypatch.setattr(settings, "STORAGE_ROOT", storage_root)

    monkeypatch.setattr(storage_paths, "STORAGE_ROOT", storage_root)

    for module in (storage_paths, storage_manager_module):
        monkeypatch.setattr(module, "RAW_HTML_DIR", raw_html_dir)
        monkeypatch.setattr(module, "SCREENSHOTS_DIR", screenshots_dir)
        monkeypatch.setattr(module, "PROCESSED_DIR", processed_dir)
        monkeypatch.setattr(module, "EXPORTS_DIR", exports_dir)

    for directory in (raw_html_dir, screenshots_dir, processed_dir, exports_dir):
        directory.mkdir(parents=True, exist_ok=True)

    return storage_root


@pytest.fixture
def sample_site(tmp_path) -> Generator[dict[str, str], None, None]:
    """Serve a deterministic local site for scraper and pipeline tests."""
    site_dir = tmp_path / "site"
    site_dir.mkdir(parents=True, exist_ok=True)

    (site_dir / "index.html").write_text(
        """
        <html>
          <head><title>Pipeline Test Page</title></head>
          <body>
            <h1>Pipeline Test Page</h1>
            <p>This page is served locally for scraper and orchestrator validation.</p>
            <table>
              <tr><th>Name</th><th>Value</th></tr>
              <tr><td>Alpha</td><td>1</td></tr>
            </table>
            <a href="/files/report.pdf">Quarterly Report</a>
          </body>
        </html>
        """,
        encoding="utf-8",
    )
    (site_dir / "robots.txt").write_text("User-agent: *\nAllow: /\n", encoding="utf-8")
    files_dir = site_dir / "files"
    files_dir.mkdir(parents=True, exist_ok=True)
    (files_dir / "report.pdf").write_bytes(b"%PDF-1.4 test fixture")

    handler = partial(SimpleHTTPRequestHandler, directory=str(site_dir))
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()

    base_url = f"http://127.0.0.1:{server.server_port}"
    try:
        yield {
            "base_url": base_url,
            "page_url": f"{base_url}/index.html",
            "run_id": f"test-{uuid4()}",
        }
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)

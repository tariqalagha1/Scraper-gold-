from pathlib import Path

import pytest

from app.api.v1.exports import download_export
from app.models.export import Export
from app.models.job import Job
from app.models.run import Run
from app.models.user import User
from app.storage.manager import StorageManager


@pytest.mark.asyncio
async def test_download_export_uses_resolved_storage_path(db_session, isolated_storage):
    storage = StorageManager()

    user = User(email="exports@example.com", hashed_password="hashed-password")
    db_session.add(user)
    await db_session.flush()

    job = Job(user_id=user.id, url="https://example.com", scrape_type="general", status="completed")
    db_session.add(job)
    await db_session.flush()

    run = Run(job_id=job.id, status="completed", progress=100)
    db_session.add(run)
    await db_session.flush()

    export = Export(
        run_id=run.id,
        format="pdf",
        file_path="exports/test-export.pdf",
        file_size=12,
    )
    db_session.add(export)
    await db_session.commit()

    export_path = Path(isolated_storage) / "exports" / "test-export.pdf"
    export_path.write_bytes(b"%PDF-1.4 test")

    response = await download_export(export.id, db_session, user, storage)

    assert Path(response.path) == export_path.resolve()
    assert Path(response.path).exists()


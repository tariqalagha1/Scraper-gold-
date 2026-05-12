from pathlib import Path

import pytest
from fastapi.responses import FileResponse
from sqlalchemy import func, select

from app.api.v1.exports import create_export, download_export, download_multiple_exports
from app.models.export import Export
from app.models.job import Job
from app.models.run import Run
from app.models.user import User
from app.schemas.export import ExportCreate
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


@pytest.mark.asyncio
async def test_download_multiple_exports_returns_native_file_for_single_export(db_session, isolated_storage):
    storage = StorageManager()

    user = User(email="exports-single@example.com", hashed_password="hashed-password")
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
        file_path="exports/test-single.pdf",
        file_size=12,
    )
    db_session.add(export)
    await db_session.commit()

    export_path = Path(isolated_storage) / "exports" / "test-single.pdf"
    export_path.write_bytes(b"%PDF-1.4 test")

    response = await download_multiple_exports([export.id], db_session, user, storage)

    assert isinstance(response, FileResponse)
    assert Path(response.path) == export_path.resolve()
    assert response.filename.endswith(".pdf")


@pytest.mark.asyncio
async def test_create_export_reuses_completed_pipeline_export_without_queue(
    db_session,
    isolated_storage,
    monkeypatch,
):
    storage = StorageManager()

    user = User(email="exports-reuse@example.com", hashed_password="hashed-password")
    db_session.add(user)
    await db_session.flush()

    job = Job(user_id=user.id, url="https://example.com", scrape_type="general", status="completed")
    db_session.add(job)
    await db_session.flush()

    run = Run(job_id=job.id, status="completed", progress=100)
    db_session.add(run)
    await db_session.flush()

    existing_export = Export(
        run_id=run.id,
        format="pdf",
        file_path="exports/reuse-existing.pdf",
        file_size=18,
    )
    db_session.add(existing_export)
    await db_session.commit()

    export_path = Path(isolated_storage) / "exports" / "reuse-existing.pdf"
    export_path.write_bytes(b"%PDF-1.4 existing")

    response = await create_export(
        export_data=ExportCreate(run_id=run.id, format="pdf"),
        db=db_session,
        current_user=user,
        api_key="dev-api-key-change-me",
        storage=storage,
    )

    assert response.id == existing_export.id
    assert response.status == "completed"
    assert response.file_path == "exports/reuse-existing.pdf"

    export_count = await db_session.scalar(select(func.count(Export.id)).where(Export.run_id == run.id))
    assert int(export_count or 0) == 1

from pathlib import Path
import json

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.models.export import Export
from app.models.job import Job
from app.models.result import Result
from app.models.run import Run
from app.models.user import User
from app.queue import tasks
from app.storage.manager import StorageManager

pytestmark = pytest.mark.asyncio


async def test_execute_scraping_job_persists_run_results_and_exports(test_engine, isolated_storage, monkeypatch):
    session_factory = async_sessionmaker(test_engine, expire_on_commit=False)
    monkeypatch.setattr(tasks, "async_session_factory", session_factory)

    storage = StorageManager()
    html_path = storage.save_raw_html("run-worker", "https://example.com/page", "<html>hello</html>")
    screenshot_path = storage.save_screenshot("run-worker", "https://example.com/page", b"png")
    excel_path = storage.save_export("run-worker", "excel", b"excel-bytes")
    pdf_path = storage.save_export("run-worker", "pdf", b"pdf-bytes")
    word_path = storage.save_export("run-worker", "word", b"word-bytes")

    async def fake_run_pipeline(input_data):
        return {
            "status": "completed",
            "raw_data": {
                "final_url": input_data["url"],
                "html_path": html_path,
                "screenshot_path": screenshot_path,
                "pages": [{"url": input_data["url"]}],
            },
            "processed_data": {
                "summary": "Captured summary",
                "page_type": "general",
                "cleaned_text": "hello world",
                "items": [{"content": "hello world"}],
            },
            "export_paths": {
                "excel_path": excel_path,
                "pdf_path": pdf_path,
                "word_path": word_path,
            },
            "errors": [],
            "finished_at": "2026-03-22T12:00:00+00:00",
        }

    monkeypatch.setattr(tasks, "run_pipeline", fake_run_pipeline)

    async with session_factory() as session:
        user = User(email="worker@example.com", hashed_password="hashed", is_active=True)
        session.add(user)
        await session.flush()
        job = Job(
            user_id=user.id,
            url="https://example.com/page",
            scrape_type="general",
            config={"respect_robots_txt": False},
            status="pending",
        )
        session.add(job)
        await session.commit()
        job_id = str(job.id)
        user_id = str(user.id)
        persisted_job_id = job.id

    result = await tasks._execute_scraping_job(job_id, user_id)

    assert result["status"] == "completed"
    assert result["progress"] == 100
    assert result["pages_scraped"] == 1

    async with session_factory() as session:
        refreshed_job = await session.scalar(select(Job).where(Job.id == persisted_job_id))
        runs = (await session.execute(select(Run).where(Run.job_id == persisted_job_id))).scalars().all()
        persisted_results = (await session.execute(select(Result).where(Result.run_id == runs[0].id))).scalars().all()
        exports = (await session.execute(select(Export).where(Export.run_id == runs[0].id))).scalars().all()

    assert refreshed_job is not None
    assert refreshed_job.status == "completed"
    assert len(runs) == 1
    assert runs[0].status == "completed"
    assert runs[0].progress == 100
    assert runs[0].pages_scraped == 1
    assert runs[0].started_at is not None
    assert runs[0].finished_at is not None
    assert runs[0].error_message is None
    assert len(persisted_results) == 1
    assert persisted_results[0].data_json["summary"] == "Captured summary"
    assert persisted_results[0].data_json["result"]["data"][0]["content"] == "hello world"
    assert persisted_results[0].data_json["execution"]["validation"]["status"] == "unknown"
    assert len(exports) == 3
    assert {export.format for export in exports} == {"excel", "pdf", "word"}


async def test_execute_scraping_job_marks_failed_run_with_error_message(test_engine, isolated_storage, monkeypatch):
    session_factory = async_sessionmaker(test_engine, expire_on_commit=False)
    monkeypatch.setattr(tasks, "async_session_factory", session_factory)

    async def failing_pipeline(input_data):
        raise RuntimeError("pipeline exploded")

    monkeypatch.setattr(tasks, "run_pipeline", failing_pipeline)

    async with session_factory() as session:
        user = User(email="failed-worker@example.com", hashed_password="hashed", is_active=True)
        session.add(user)
        await session.flush()
        job = Job(
            user_id=user.id,
            url="https://example.com/fail",
            scrape_type="general",
            config={},
            status="pending",
        )
        session.add(job)
        await session.commit()
        job_id = str(job.id)
        user_id = str(user.id)
        persisted_job_id = job.id

    result = await tasks._execute_scraping_job(job_id, user_id)

    assert result["status"] == "failed"
    assert result["error"] == "pipeline exploded"

    async with session_factory() as session:
        refreshed_job = await session.scalar(select(Job).where(Job.id == persisted_job_id))
        run = (await session.execute(select(Run).where(Run.job_id == persisted_job_id))).scalars().one()

    assert refreshed_job is not None
    assert refreshed_job.status == "failed"
    assert run.status == "failed"
    assert run.started_at is not None
    assert run.finished_at is not None
    assert run.error_message == "pipeline exploded"


async def test_execute_scraping_job_uses_existing_run_when_run_id_is_provided(test_engine, isolated_storage, monkeypatch):
    session_factory = async_sessionmaker(test_engine, expire_on_commit=False)
    monkeypatch.setattr(tasks, "async_session_factory", session_factory)

    async def fake_run_pipeline(input_data):
        return {
            "status": "completed",
            "raw_data": {"final_url": input_data["url"], "pages": [{"url": input_data["url"]}]},
            "processed_data": {"summary": "ok", "page_type": "general", "cleaned_text": "body"},
            "export_paths": {},
            "errors": [],
            "finished_at": "2026-03-22T12:00:00+00:00",
        }

    monkeypatch.setattr(tasks, "run_pipeline", fake_run_pipeline)

    async with session_factory() as session:
        user = User(email="existing-run@example.com", hashed_password="hashed", is_active=True)
        session.add(user)
        await session.flush()
        job = Job(
            user_id=user.id,
            url="https://example.com/existing",
            scrape_type="general",
            config={},
            status="pending",
        )
        session.add(job)
        await session.flush()
        run = Run(job_id=job.id, status="pending", progress=0)
        session.add(run)
        await session.commit()
        job_id = str(job.id)
        user_id = str(user.id)
        run_id = str(run.id)
        persisted_job_id = job.id

    result = await tasks._execute_scraping_job(job_id, user_id, run_id)

    assert result["status"] == "completed"
    assert result["run_id"] == run_id

    async with session_factory() as session:
        runs = (await session.execute(select(Run).where(Run.job_id == persisted_job_id))).scalars().all()

    assert len(runs) == 1
    assert str(runs[0].id) == run_id
    assert runs[0].status == "completed"
    assert runs[0].progress == 100


async def test_execute_scraping_job_rejects_duplicate_active_run(test_engine, isolated_storage, monkeypatch):
    session_factory = async_sessionmaker(test_engine, expire_on_commit=False)
    monkeypatch.setattr(tasks, "async_session_factory", session_factory)

    async def fake_run_pipeline(input_data):
        return {
            "status": "completed",
            "raw_data": {"final_url": input_data["url"], "pages": [{"url": input_data["url"]}]},
            "processed_data": {"summary": "ok", "page_type": "general", "cleaned_text": "body"},
            "export_paths": {},
            "errors": [],
            "finished_at": "2026-03-22T12:00:00+00:00",
        }

    monkeypatch.setattr(tasks, "run_pipeline", fake_run_pipeline)

    async with session_factory() as session:
        user = User(email="duplicate-worker@example.com", hashed_password="hashed", is_active=True)
        session.add(user)
        await session.flush()
        job = Job(
            user_id=user.id,
            url="https://example.com/duplicate-worker",
            scrape_type="general",
            config={},
            status="pending",
        )
        session.add(job)
        await session.flush()
        existing_run = Run(job_id=job.id, status="running", progress=40)
        session.add(existing_run)
        await session.commit()
        job_id = str(job.id)
        user_id = str(user.id)
        persisted_job_id = job.id

    result = await tasks._execute_scraping_job(job_id, user_id)

    assert result["status"] == "failed"
    assert result["error"] == "A run is already pending or running for this job."
    assert result["run_id"] == str(existing_run.id)

    async with session_factory() as session:
        runs = (await session.execute(select(Run).where(Run.job_id == persisted_job_id))).scalars().all()

    assert len(runs) == 1
    assert runs[0].status == "running"


async def test_execute_export_updates_export_record_with_generated_file(test_engine, isolated_storage, monkeypatch):
    session_factory = async_sessionmaker(test_engine, expire_on_commit=False)
    monkeypatch.setattr(tasks, "async_session_factory", session_factory)

    class StubExporter:
        async def export(
            self,
            processed_data,
            *,
            export_id=None,
            source_url="",
            title="",
            analysis_data=None,
            generated_at=None,
        ):
            storage = StorageManager()
            return storage.save_export(export_id or "fallback", "pdf", b"rendered-pdf")

    monkeypatch.setattr(tasks, "_get_exporter", lambda export_format: StubExporter())

    async with session_factory() as session:
        user = User(email="export@example.com", hashed_password="hashed", is_active=True)
        session.add(user)
        await session.flush()
        job = Job(
            user_id=user.id,
            url="https://example.com/page",
            scrape_type="general",
            config={},
            status="completed",
        )
        session.add(job)
        await session.flush()
        run = Run(job_id=job.id, status="completed")
        session.add(run)
        await session.flush()
        result = Result(
            run_id=run.id,
            data_json={"summary": "ok", "page_type": "general", "cleaned_text": "body"},
            data_type="general",
            url="https://example.com/page",
        )
        export = Export(run_id=run.id, format="pdf", file_path="")
        session.add_all([result, export])
        await session.commit()
        export_id = str(export.id)
        persisted_export_id = export.id
        user_id = str(user.id)

    execution = await tasks._execute_export(export_id, user_id)

    assert execution["status"] == "completed"

    async with session_factory() as session:
        refreshed_export = await session.scalar(select(Export).where(Export.id == persisted_export_id))

    assert refreshed_export is not None
    assert refreshed_export.file_path
    assert refreshed_export.file_size and refreshed_export.file_size > 0
    assert Path(refreshed_export.file_path).suffix.lower() == ".pdf"


async def test_execute_scraping_job_persists_normalized_contract_in_result_payload(test_engine, isolated_storage, monkeypatch):
    session_factory = async_sessionmaker(test_engine, expire_on_commit=False)
    monkeypatch.setattr(tasks, "async_session_factory", session_factory)

    async def fake_run_pipeline(input_data):
        return {
            "status": "completed",
            "url": input_data["url"],
            "scraping_type": "general",
            "raw_data": {"final_url": input_data["url"], "pages": [{"url": input_data["url"]}]},
            "processed_data": {
                "summary": "Captured summary",
                "page_type": "general",
                "cleaned_text": "body",
                "items": [{"title": "One", "price": "10"}],
            },
            "analysis_data": {"status": "success"},
            "vector_data": {"optional": True},
            "export_paths": {},
            "errors": [],
            "config": {"respect_robots_txt": False},
            "strategy": {"use_javascript": True},
            "validation": {
                "status": "pass",
                "confidence": 0.91,
                "issues": [],
                "metrics": {"records": 1},
                "should_retry": False,
            },
            "retry": False,
            "trace": {
                "classification": {
                    "page_type": "list",
                    "confidence": 0.82,
                    "reason": "collection page",
                },
                "memory_used": False,
                "selector_source": "generated",
                "memory_success_rate": None,
                "retry_attempted": False,
            },
            "job_id": input_data["job_id"],
            "run_id": input_data["run_id"],
            "user_id": input_data["user_id"],
            "current_step": "export",
            "started_at": "2026-03-24T12:00:00+00:00",
            "finished_at": "2026-03-24T12:00:01+00:00",
            "node_timings": {"scraper": 1.0},
        }

    monkeypatch.setattr(tasks, "run_pipeline", fake_run_pipeline)

    async with session_factory() as session:
        user = User(email="contract-worker@example.com", hashed_password="hashed", is_active=True)
        session.add(user)
        await session.flush()
        job = Job(
            user_id=user.id,
            url="https://example.com/contract",
            scrape_type="general",
            config={"respect_robots_txt": False},
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
        persisted_result = (await session.execute(select(Result).where(Result.run_id == run.id))).scalars().one()

    assert persisted_result.data_json["summary"] == "Captured summary"
    assert persisted_result.data_json["request"]["url"] == "https://example.com/contract"
    assert persisted_result.data_json["result"]["data"][0]["title"] == "One"
    assert persisted_result.data_json["execution"]["validation"]["status"] == "pass"
    assert persisted_result.data_json["metadata"]["duration_ms"] == 1000


async def test_execute_export_generates_json_contract_file(test_engine, isolated_storage, monkeypatch):
    session_factory = async_sessionmaker(test_engine, expire_on_commit=False)
    monkeypatch.setattr(tasks, "async_session_factory", session_factory)

    async with session_factory() as session:
        user = User(email="json-export@example.com", hashed_password="hashed", is_active=True)
        session.add(user)
        await session.flush()
        job = Job(
            user_id=user.id,
            url="https://example.com/json",
            scrape_type="general",
            config={},
            status="completed",
        )
        session.add(job)
        await session.flush()
        run = Run(job_id=job.id, status="completed")
        session.add(run)
        await session.flush()
        result = Result(
            run_id=run.id,
            data_json={
                "request": {"url": "https://example.com/json", "scrape_type": "general", "config": {}, "strategy": {}},
                "result": {"data": [{"title": "One"}], "raw": {}, "processed": {"summary": "ok"}, "analysis": {}, "vector": {}, "exports": {}},
                "execution": {
                    "decision": {"page_type": "detail", "confidence": 0.9, "reason": "item page"},
                    "validation": {"status": "pass", "confidence": 0.9, "issues": [], "metrics": {"records": 1}, "should_retry": False},
                    "retry": {"attempted": False, "result": False},
                    "memory": {"used": False, "selector_source": "generated", "success_rate": None},
                    "timing": {},
                    "steps": {"current": "completed"},
                    "trace": {},
                },
                "metadata": {"run_id": str(run.id), "job_id": str(job.id), "user_id": str(user.id), "started_at": "", "finished_at": "", "duration_ms": 0},
                "errors": [],
                "status": "completed",
            },
            data_type="general",
            url="https://example.com/json",
        )
        export = Export(run_id=run.id, format="json", file_path="")
        session.add_all([result, export])
        await session.commit()
        export_id = str(export.id)
        persisted_export_id = export.id
        user_id = str(user.id)

    execution = await tasks._execute_export(export_id, user_id)
    assert execution["status"] == "completed"

    async with session_factory() as session:
        refreshed_export = await session.scalar(select(Export).where(Export.id == persisted_export_id))

    assert refreshed_export is not None
    assert refreshed_export.file_path.endswith(".json")
    export_path = StorageManager().resolve_path(refreshed_export.file_path)
    payload = json.loads(export_path.read_text(encoding="utf-8"))
    assert payload["request"]["url"] == "https://example.com/json"
    assert payload["result"]["data"][0]["title"] == "One"
    assert payload["execution"]["decision"]["page_type"] == "detail"


async def test_execute_scraping_job_persists_failed_contract_for_export_use(test_engine, isolated_storage, monkeypatch):
    session_factory = async_sessionmaker(test_engine, expire_on_commit=False)
    monkeypatch.setattr(tasks, "async_session_factory", session_factory)

    async def failed_pipeline(input_data):
        return {
            "status": "failed",
            "url": input_data["url"],
            "scraping_type": "general",
            "raw_data": {},
            "processed_data": {},
            "analysis_data": {},
            "vector_data": {},
            "export_paths": {},
            "errors": ["No extracted data was found."],
            "validation": {
                "status": "fail",
                "confidence": 0.0,
                "issues": ["No extracted data was found."],
                "metrics": {"records": 0, "fill_ratio": 0.0, "duplicate_ratio": 0.0},
                "should_retry": True,
            },
            "trace": {
                "classification": {
                    "page_type": "list",
                    "confidence": 0.82,
                    "reason": "collection page",
                },
                "memory_used": False,
                "selector_source": "generated",
                "memory_success_rate": None,
                "retry_attempted": True,
            },
            "job_id": input_data["job_id"],
            "run_id": input_data["run_id"],
            "user_id": input_data["user_id"],
            "current_step": "scraper",
            "started_at": "2026-03-24T12:00:00+00:00",
            "finished_at": "2026-03-24T12:00:05+00:00",
            "node_timings": {"scraper": 5.0},
        }

    monkeypatch.setattr(tasks, "run_pipeline", failed_pipeline)

    async with session_factory() as session:
        user = User(email="failed-contract@example.com", hashed_password="hashed", is_active=True)
        session.add(user)
        await session.flush()
        job = Job(
            user_id=user.id,
            url="https://example.com/failed-contract",
            scrape_type="general",
            config={},
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
        persisted_result = (await session.execute(select(Result).where(Result.run_id == run.id))).scalars().one()

    assert persisted_result.data_json["status"] == "failed"
    assert persisted_result.data_json["result"]["data"] == []
    assert persisted_result.data_json["execution"]["validation"]["status"] == "fail"
    assert persisted_result.data_json["errors"] == ["No extracted data was found."]

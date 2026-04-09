import asyncio
import hashlib
import json
import os
from datetime import datetime, timezone
from threading import local
from typing import Any
from uuid import UUID

from redis.asyncio import Redis
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.config import settings
from app.core.logging import get_agent_logger
from app.db.session import async_session_factory
from app.export.excel import ExcelExporter
from app.export.json import JSONExporter
from app.export.pdf import PDFExporter
from app.export.word import WordExporter
from app.models.export import Export
from app.models.job import Job
from app.models.result import Result
from app.models.run import Run
from app.orchestrator import SmartOrchestrator
from app.export.contract_helpers import build_persisted_result_payload
from app.queue.celery_app import celery_app
from app.services.run_logs import append_run_log
from app.services.user_credentials import get_user_provider_credentials
from app.storage.manager import StorageManager


logger = get_agent_logger("queue.tasks")
storage_manager = StorageManager()
smart_orchestrator = SmartOrchestrator()
_worker_runtime = local()


async def run_pipeline(input_data: dict[str, Any]) -> dict[str, Any]:
    """Backward-compatible execution entrypoint for task tests and wrappers."""
    return await smart_orchestrator.run(input_data)


def _payload_hash(payload: dict[str, Any]) -> str:
    return hashlib.sha256(json.dumps(payload, sort_keys=True, default=str).encode("utf-8")).hexdigest()


async def _get_redis() -> Redis:
    return Redis.from_url(settings.REDIS_URL, decode_responses=True, socket_timeout=settings.REDIS_CONNECT_TIMEOUT)


async def _acquire_task_lock(task_name: str, payload: dict[str, Any]) -> bool:
    try:
        client = await _get_redis()
        key = f"idempotency:{task_name}:{_payload_hash(payload)}"
        acquired = await client.set(key, "1", ex=settings.CELERY_TASK_TIME_LIMIT, nx=True)
        await client.close()
        return bool(acquired)
    except Exception as exc:
        logger.error("Task idempotency backend unavailable; failing closed.", task=task_name, error=str(exc))
        return False


def run_async(coroutine: Any) -> Any:
    loop = _get_worker_event_loop()
    return loop.run_until_complete(coroutine)


def _get_worker_event_loop() -> asyncio.AbstractEventLoop:
    current_pid = os.getpid()
    loop = getattr(_worker_runtime, "loop", None)
    loop_pid = getattr(_worker_runtime, "loop_pid", None)
    if loop is None or loop.is_closed() or loop_pid != current_pid:
        if loop is not None and not loop.is_closed():
            loop.close()
        loop = asyncio.new_event_loop()
        _worker_runtime.loop = loop
        _worker_runtime.loop_pid = current_pid
    asyncio.set_event_loop(loop)
    return loop


def _reset_worker_event_loop() -> None:
    loop = getattr(_worker_runtime, "loop", None)
    if loop is not None and not loop.is_closed():
        loop.close()
    _worker_runtime.loop = None
    _worker_runtime.loop_pid = None


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _parse_uuid(value: str) -> UUID:
    return UUID(str(value))


def _coerce_datetime(value: Any) -> datetime | None:
    if not value:
        return None
    if isinstance(value, datetime):
        return value
    try:
        return datetime.fromisoformat(str(value))
    except ValueError:
        return None


def _summarize_errors(errors: list[str]) -> str | None:
    cleaned = [str(error).strip() for error in errors if str(error).strip()]
    if not cleaned:
        return None
    return " | ".join(cleaned)


def _safe_error_message(exc: Exception | str) -> str:
    text = str(exc).strip() if exc is not None else ""
    return text or "Run execution failed."


def _resolve_pages_scraped(raw_data: dict[str, Any]) -> int:
    pages = raw_data.get("pages", [])
    if isinstance(pages, list) and pages:
        return len(pages)
    if raw_data.get("html_path") or raw_data.get("final_url"):
        return 1
    return 0


def _export_format_from_key(key: str) -> str | None:
    return {
        "excel_path": "excel",
        "pdf_path": "pdf",
        "word_path": "word",
    }.get(key)


def _get_exporter(export_format: str) -> Any:
    exporter_cls = {
        "excel": ExcelExporter,
        "pdf": PDFExporter,
        "word": WordExporter,
        "json": JSONExporter,
    }.get(export_format.strip().lower())
    if exporter_cls is None:
        raise ValueError(f"Unsupported export format: {export_format}")
    return exporter_cls()


async def _load_job(session: Any, job_id: str, user_id: str) -> Job | None:
    stmt = (
        select(Job)
        .where(Job.id == _parse_uuid(job_id), Job.user_id == _parse_uuid(user_id))
        .options(selectinload(Job.runs))
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def _load_run(session: Any, run_id: str, job_id: str) -> Run | None:
    stmt = select(Run).where(Run.id == _parse_uuid(run_id), Run.job_id == _parse_uuid(job_id))
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def _load_active_run(session: Any, job_id: str, *, exclude_run_id: str | None = None) -> Run | None:
    stmt = select(Run).where(
        Run.job_id == _parse_uuid(job_id),
        Run.status.in_(("pending", "running")),
    )
    if exclude_run_id:
        stmt = stmt.where(Run.id != _parse_uuid(exclude_run_id))
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def _load_export(session: Any, export_id: str, user_id: str) -> Export | None:
    stmt = (
        select(Export)
        .join(Run, Export.run_id == Run.id)
        .join(Job, Run.job_id == Job.id)
        .where(Export.id == _parse_uuid(export_id), Job.user_id == _parse_uuid(user_id))
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def _load_latest_run_result(session: Any, run_id: UUID) -> Result | None:
    stmt = select(Result).where(Result.run_id == run_id).order_by(Result.created_at.desc())
    result = await session.execute(stmt)
    return result.scalars().first()


async def _persist_pipeline_records(
    session: Any,
    *,
    job: Job,
    run: Run,
    workflow_result: dict[str, Any],
) -> None:
    raw_data = workflow_result.get("raw_data") or {}
    export_paths = workflow_result.get("export_paths") or {}
    persisted_payload = build_persisted_result_payload(workflow_result)

    run.status = "completed" if workflow_result.get("status") == "completed" else "failed"
    run.finished_at = _coerce_datetime(workflow_result.get("finished_at")) or _utcnow()
    run.error = _summarize_errors(workflow_result.get("errors", []))
    run.error_message = run.error
    run.pages_scraped = _resolve_pages_scraped(raw_data)
    compression_ratio = workflow_result.get("token_compression_ratio")
    try:
        run.token_compression_ratio = float(compression_ratio) if compression_ratio is not None else None
    except (TypeError, ValueError):
        run.token_compression_ratio = None
    run.stealth_engaged = bool(workflow_result.get("stealth_engaged", False))
    run.markdown_snapshot_path = str(workflow_result.get("markdown_snapshot_path") or "").strip() or None
    job.status = run.status

    if persisted_payload:
        session.add(
            Result(
                run_id=run.id,
                data_json=persisted_payload,
                data_type=job.scrape_type,
                raw_html_path=raw_data.get("html_path"),
                screenshot_path=raw_data.get("screenshot_path"),
                url=raw_data.get("final_url") or workflow_result.get("url") or job.url,
            )
        )

    for key, path in export_paths.items():
        export_format = _export_format_from_key(key)
        if not export_format or not path:
            continue
        session.add(
            Export(
                run_id=run.id,
                format=export_format,
                file_path=path,
                file_size=storage_manager.get_file_size(path),
            )
        )

    await session.commit()


async def _persist_failed_run(session: Any, *, job: Job, run: Run, error: str) -> None:
    run.status = "failed"
    run.finished_at = _utcnow()
    run.error = error
    run.error_message = error
    job.status = "failed"
    await session.commit()


async def _commit_progress(
    session: Any,
    *,
    job: Job,
    run: Run,
    status: str | None = None,
    progress: int | None = None,
    started_at: datetime | None = None,
    finished_at: datetime | None = None,
    error_message: str | None = None,
) -> None:
    if status is not None:
        run.status = status
        job.status = status
    if progress is not None:
        run.progress = max(0, min(100, progress))
    if started_at is not None:
        run.started_at = started_at
    if finished_at is not None:
        run.finished_at = finished_at
    if error_message is not None:
        run.error_message = error_message
        run.error = error_message
    await session.commit()


async def _execute_scraping_job(job_id: str, user_id: str, run_id: str | None = None) -> dict[str, Any]:
    async with async_session_factory() as session:
        job = await _load_job(session, job_id, user_id)
        if job is None:
            message = f"Job {job_id} was not found for user {user_id}."
            logger.warning(message)
            return {"status": "failed", "error": message, "job_id": job_id, "user_id": user_id}

        if run_id:
            run = await _load_run(session, run_id, job_id)
            if run is None:
                message = f"Run {run_id} was not found for job {job_id}."
                logger.warning(message)
                return {"status": "failed", "error": message, "job_id": job_id, "user_id": user_id, "run_id": run_id}
            if run.status in {"running", "completed"}:
                message = f"Run {run_id} is already {run.status}."
                logger.info(message, job_id=job_id, run_id=run_id)
                return {
                    "status": run.status,
                    "job_id": job_id,
                    "run_id": run_id,
                    "progress": run.progress,
                    "error": None,
                }
            active_run = await _load_active_run(session, job_id, exclude_run_id=run_id)
            if active_run:
                message = "A run is already pending or running for this job."
                logger.warning(message, job_id=job_id, run_id=run_id, active_run_id=str(active_run.id))
                append_run_log(str(run.id), event="duplicate_blocked", message=message, level="error")
                await _commit_progress(
                    session,
                    job=job,
                    run=run,
                    status="failed",
                    finished_at=_utcnow(),
                    error_message=message,
                )
                return {
                    "status": "failed",
                    "job_id": job_id,
                    "run_id": run_id,
                    "error": message,
                }
        else:
            active_run = await _load_active_run(session, job_id)
            if active_run:
                run = active_run
                if run.status == "running":
                    message = f"Run {run.id} is already running."
                    logger.info(message, job_id=job_id, run_id=str(run.id))
                    return {
                        "status": run.status,
                        "job_id": job_id,
                        "run_id": str(run.id),
                        "progress": run.progress,
                        "error": None,
                    }
                logger.info(
                    "Reusing existing pending run for retry-safe execution.",
                    job_id=job_id,
                    run_id=str(run.id),
                )
                append_run_log(
                    str(run.id),
                    event="retry_reused_run",
                    message="Reusing existing pending run for retry-safe execution.",
                )
            else:
                run = Run(job_id=job.id, status="pending", progress=0)
                session.add(run)
                await session.commit()
                await session.refresh(run)
        started_at = _utcnow()
        append_run_log(str(run.id), event="run_started", message="Run execution started.")
        await _commit_progress(
            session,
            job=job,
            run=run,
            status="running",
            progress=5,
            started_at=started_at,
            error_message=None,
        )

        credentials = {}
        if job.login_username and job.login_password:
            credentials = {
                "login_url": job.login_url,
                "username": job.login_username,
                "password": job.login_password,
            }
        provider_credentials = await get_user_provider_credentials(session, user_id=job.user_id)
        if provider_credentials:
            credentials["providers"] = provider_credentials

        try:
            await _commit_progress(session, job=job, run=run, progress=20)
            append_run_log(str(run.id), event="pipeline_started", message="Pipeline execution started.")
            workflow_result = await asyncio.wait_for(
                run_pipeline(
                    {
                        "job_id": str(job.id),
                        "run_id": str(run.id),
                        "user_id": str(job.user_id),
                        "url": job.url,
                        "scrape_type": job.scrape_type,
                        "credentials": credentials,
                        "config": job.config or {},
                    }
                ),
                timeout=settings.CELERY_TASK_TIME_LIMIT,
            )
            await _commit_progress(session, job=job, run=run, progress=50)
            append_run_log(str(run.id), event="pipeline_finished", message="Pipeline execution finished.")
        except asyncio.TimeoutError:
            message = "Run exceeded maximum execution time."
            logger.error(
                "Scraping job execution timed out.",
                job_id=str(job.id),
                run_id=str(run.id),
                error=message,
            )
            append_run_log(str(run.id), event="timeout", message=message, level="error")
            await _commit_progress(
                session,
                job=job,
                run=run,
                status="failed",
                finished_at=_utcnow(),
                error_message=message,
            )
            return {
                "status": "failed",
                "job_id": str(job.id),
                "run_id": str(run.id),
                "error": message,
            }
        except Exception as exc:
            message = _safe_error_message(exc)
            logger.error(
                "Scraping job execution failed unexpectedly.",
                job_id=str(job.id),
                run_id=str(run.id),
                error=message,
                exc_info=True,
            )
            append_run_log(str(run.id), event="run_failed", message=message, level="error")
            await _commit_progress(
                session,
                job=job,
                run=run,
                status="failed",
                finished_at=_utcnow(),
                error_message=message,
            )
            return {
                "status": "failed",
                "job_id": str(job.id),
                "run_id": str(run.id),
                "error": message,
            }

        await _commit_progress(session, job=job, run=run, progress=80)
        append_run_log(str(run.id), event="persisting_results", message="Persisting run outputs.")
        try:
            await _persist_pipeline_records(session, job=job, run=run, workflow_result=workflow_result)
        except Exception as exc:
            message = _safe_error_message(exc)
            logger.error(
                "Failed while persisting scraping run outputs.",
                job_id=str(job.id),
                run_id=str(run.id),
                error=message,
                exc_info=True,
            )
            append_run_log(str(run.id), event="persist_failed", message=message, level="error")
            await session.rollback()
            await _commit_progress(
                session,
                job=job,
                run=run,
                status="failed",
                finished_at=_utcnow(),
                error_message=message,
            )
            return {
                "status": "failed",
                "job_id": str(job.id),
                "run_id": str(run.id),
                "error": message,
            }
        await session.refresh(run)
        if run.status == "completed":
            append_run_log(str(run.id), event="run_completed", message="Run completed successfully.")
            await _commit_progress(
                session,
                job=job,
                run=run,
                status="completed",
                progress=100,
                finished_at=run.finished_at or _utcnow(),
                error_message=None,
            )
        else:
            append_run_log(
                str(run.id),
                event="run_failed",
                message=run.error_message or run.error or "Run failed",
                level="error",
            )
            await _commit_progress(
                session,
                job=job,
                run=run,
                status="failed",
                finished_at=run.finished_at or _utcnow(),
                error_message=run.error_message or run.error or "Run failed",
            )
        await session.refresh(run)
        return {
            "status": run.status,
            "job_id": str(job.id),
            "run_id": str(run.id),
            "progress": run.progress,
            "pages_scraped": run.pages_scraped,
            "errors": workflow_result.get("errors", []),
        }


async def _execute_export(export_id: str, user_id: str) -> dict[str, Any]:
    async with async_session_factory() as session:
        export = await _load_export(session, export_id, user_id)
        if export is None:
            message = f"Export {export_id} was not found for user {user_id}."
            logger.warning(message)
            return {"status": "failed", "error": message, "export_id": export_id, "user_id": user_id}

        if export.run_id is None:
            message = f"Export {export_id} is not attached to a run."
            logger.warning(message)
            return {"status": "failed", "error": message, "export_id": export_id}

        result = await _load_latest_run_result(session, export.run_id)
        if result is None:
            message = f"Run {export.run_id} has no persisted results to export."
            logger.warning(message, export_id=str(export.id), run_id=str(export.run_id))
            return {"status": "failed", "error": message, "export_id": str(export.id)}

        try:
            exporter = _get_exporter(export.format)
            file_path = await exporter.export(
                result.data_json,
                export_id=str(export.id),
                source_url=result.url,
                title="Processed Web Data Export",
            )
        except Exception as exc:
            logger.error(
                "Export generation failed unexpectedly.",
                export_id=str(export.id),
                run_id=str(export.run_id),
                error=str(exc),
                exc_info=True,
            )
            return {"status": "failed", "error": str(exc), "export_id": str(export.id)}

        export.file_path = file_path
        export.file_size = storage_manager.get_file_size(file_path)
        try:
            await session.commit()
        except Exception as exc:
            await session.rollback()
            logger.error(
                "Failed while persisting export metadata.",
                export_id=str(export.id),
                run_id=str(export.run_id),
                error=str(exc),
                exc_info=True,
            )
            return {
                "status": "failed",
                "error": f"Failed to persist export metadata: {exc}",
                "export_id": str(export.id),
            }
        await session.refresh(export)

        return {
            "status": "completed",
            "export_id": str(export.id),
            "file_path": export.file_path,
            "file_size": export.file_size,
        }


@celery_app.task(name="app.queue.tasks.ping")
def ping() -> dict[str, str]:
    return {"status": "ok"}


@celery_app.task(name="app.queue.tasks.basic_async_task")
def basic_async_task(payload: dict[str, Any]) -> dict[str, Any]:
    return run_async(_run_idempotent_task("basic_async_task", payload))


async def _basic_async_task(payload: dict[str, Any]) -> dict[str, Any]:
    started_at = _utcnow().isoformat()
    await asyncio.sleep(0)
    logger.info("Processed basic async task.", payload=payload)
    return {
        "status": "success",
        "payload": payload,
        "processed_at": _utcnow().isoformat(),
        "started_at": started_at,
    }


async def _run_idempotent_task(task_name: str, payload: dict[str, Any]) -> dict[str, Any]:
    should_enforce_lock = not (
        task_name == "run_scraping_job"
        and bool(str(payload.get("run_id") or "").strip())
    )
    if should_enforce_lock and not await _acquire_task_lock(task_name, payload):
        return {
            "status": "success",
            "payload": payload,
            "processed_at": _utcnow().isoformat(),
            "started_at": _utcnow().isoformat(),
            "idempotent_skip": True,
        }
    task_routes: dict[str, dict[str, Any]] = {
        "run_scraping_job": {
            "required_keys": ("job_id", "user_id"),
            "handler": lambda task_payload: _execute_scraping_job(
                task_payload["job_id"],
                task_payload["user_id"],
                task_payload.get("run_id"),
            ),
        },
        "run_export": {
            "required_keys": ("export_id", "user_id"),
            "handler": lambda task_payload: _execute_export(
                task_payload["export_id"],
                task_payload["user_id"],
            ),
        },
        "basic_async_task": {
            "required_keys": (),
            "handler": _basic_async_task,
        },
    }

    route = task_routes.get(task_name)
    if route is None:
        raise ValueError(f"Unknown task name: {task_name}")

    missing_keys = [
        key
        for key in route["required_keys"]
        if key not in payload or payload.get(key) in (None, "")
    ]
    if missing_keys:
        raise ValueError(f"Missing required payload keys for {task_name}: {', '.join(missing_keys)}")

    handler = route["handler"]
    return await handler(payload)


@celery_app.task(name="app.queue.tasks.run_scraping_job", soft_time_limit=600, time_limit=630)
def run_scraping_job(job_id: str, user_id: str, run_id: str | None = None) -> dict[str, Any]:
    return run_async(
        _run_idempotent_task(
            "run_scraping_job",
            {
                "task": "run_scraping_job",
                "job_id": job_id,
                "user_id": user_id,
                "run_id": run_id,
            },
        )
    )


@celery_app.task(name="app.queue.tasks.run_export")
def run_export(export_id: str, user_id: str) -> dict[str, Any]:
    return run_async(
        _run_idempotent_task(
            "run_export",
            {
                "task": "run_export",
                "export_id": export_id,
                "user_id": user_id,
            },
        )
    )


@celery_app.task(name="app.queue.tasks.generate_export")
def generate_export(export_id: str, result_ids: list[Any], export_format: str) -> dict[str, Any]:
    return run_async(
        _run_idempotent_task(
            "generate_export",
            {
                "task": "generate_export",
                "export_id": export_id,
                "result_ids": result_ids,
                "export_format": export_format,
            }
        )
    )


@celery_app.task(name="app.queue.tasks.run_analysis")
def run_analysis(run_id: str, user_id: str) -> dict[str, Any]:
    return run_async(
        _run_idempotent_task(
            "run_analysis",
            {
                "task": "run_analysis",
                "run_id": run_id,
                "user_id": user_id,
            }
        )
    )

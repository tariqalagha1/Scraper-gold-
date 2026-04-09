from __future__ import annotations

import asyncio
import time
from typing import Any, Awaitable, Callable
from uuid import uuid4

from app.core.logger import safe_set_pipeline_id
from app.core.logging import get_logger
from app.config import settings
from app.orchestrator.state import WorkflowState
from app.scraper.extractor import ContentExtractor
from app.scraper.processing_helpers import html_to_semantic_markdown
from app.services.run_logs import append_run_log
from app.storage.manager import StorageManager


logger = get_logger("app.orchestrator.nodes")

extractor = ContentExtractor()
storage_manager = StorageManager()

_NODE_TIMEOUT_OVERRIDES = {
    "intake": "ORCHESTRATION_INTAKE_TIMEOUT_SECONDS",
    "scraper": "ORCHESTRATION_SCRAPER_TIMEOUT_SECONDS",
    "processing": "ORCHESTRATION_PROCESSING_TIMEOUT_SECONDS",
    "vector": "ORCHESTRATION_VECTOR_TIMEOUT_SECONDS",
    "analysis": "ORCHESTRATION_ANALYSIS_TIMEOUT_SECONDS",
    "export": "ORCHESTRATION_EXPORT_TIMEOUT_SECONDS",
}


def _node_timeout_seconds(node_name: str) -> int:
    setting_name = _NODE_TIMEOUT_OVERRIDES.get(node_name)
    if setting_name:
        return max(1, int(getattr(settings, setting_name)))
    return max(1, int(settings.ORCHESTRATION_NODE_TIMEOUT_SECONDS))


def _append_node_run_log(
    state: WorkflowState,
    *,
    event: str,
    message: str,
    level: str = "info",
    details: dict[str, Any] | None = None,
) -> None:
    if not state.run_id:
        return
    append_run_log(
        str(state.run_id),
        event=event,
        message=message,
        level=level,
        details={
            "node": state.current_step,
            "job_id": state.job_id,
            "url": state.url,
            **(details or {}),
        },
    )


def _halt_pipeline(state: WorkflowState, *, reason: str, node_name: str) -> WorkflowState:
    state.status = "failed"
    state.current_step = node_name
    state.config = {
        **(state.config or {}),
        "_halt_pipeline": True,
        "_halt_pipeline_reason": reason,
    }
    state.add_error(reason)
    return state


def _should_end(state: WorkflowState) -> bool:
    config = state.config if isinstance(state.config, dict) else {}
    return state.status == "failed" or bool(config.get("_halt_pipeline"))


def _merge_strategy(base: dict[str, Any], overrides: dict[str, Any]) -> dict[str, Any]:
    merged = dict(base or {})
    override_values = dict(overrides or {})

    base_selectors = merged.get("selectors")
    override_selectors = override_values.get("selectors")
    if isinstance(base_selectors, dict) or isinstance(override_selectors, dict):
        merged["selectors"] = {
            **(base_selectors if isinstance(base_selectors, dict) else {}),
            **(override_selectors if isinstance(override_selectors, dict) else {}),
        }

    for key, value in override_values.items():
        if key == "selectors":
            continue
        merged[key] = value
    return merged


def _aggregate_extracted_payloads(
    extracted_payloads: list[dict[str, Any]],
    *,
    source_url: str,
    scraping_type: str,
) -> dict[str, Any]:
    aggregated: dict[str, Any] = {
        "title": {"value": "", "confidence": 0.0},
        "headings": [],
        "paragraphs": [],
        "links": [],
        "files": [],
        "images": [],
        "videos": [],
        "tables": [],
        "lists": [],
        "records": [],
    }
    selector_used: list[str] = []
    total_records = 0

    for payload in extracted_payloads:
        data = payload.get("data", {}) if isinstance(payload, dict) else {}
        metadata = payload.get("metadata", {}) if isinstance(payload, dict) else {}

        title = data.get("title")
        if (
            isinstance(title, dict)
            and title.get("value")
            and not aggregated["title"]["value"]
        ):
            aggregated["title"] = title

        for key in ("headings", "paragraphs", "links", "files", "images", "videos", "tables", "lists", "records"):
            value = data.get(key)
            if isinstance(value, list):
                aggregated[key].extend(value)

        if metadata.get("selector_used"):
            selector_used.append(str(metadata["selector_used"]))
        total_records += int(metadata.get("records_extracted", 0) or 0)

    return {
        "status": "success",
        "data": aggregated,
        "error": None,
        "metadata": {
            "source_url": source_url,
            "scraping_type": scraping_type,
            "parser": "beautifulsoup+lxml",
            "selector_used": selector_used[0] if selector_used else None,
            "records_extracted": total_records,
            "pages_processed": len(extracted_payloads),
        },
    }


def _create_intake_agent():
    from app.agents.intake_agent import IntakeAgent

    return IntakeAgent()


def _create_scraper_agent():
    from app.agents.scraper_agent import ScraperAgent

    return ScraperAgent()


def _create_processing_agent():
    from app.agents.processing_agent import ProcessingAgent

    return ProcessingAgent()


def _create_vector_agent():
    from app.agents.vector_agent import VectorAgent

    return VectorAgent()


def _create_analysis_agent():
    from app.agents.analysis_agent import AnalysisAgent

    return AnalysisAgent()


def _create_export_agent():
    from app.agents.export_agent import ExportAgent

    return ExportAgent()


async def _run_logged_node(
    state: WorkflowState,
    node_name: str,
    operation: Callable[[], Awaitable[WorkflowState]],
) -> WorkflowState:
    pipeline_id = str(
        (state.config or {}).get("pipeline_id")
        or state.run_id
        or state.job_id
        or uuid4()
    )
    state.config = {**(state.config or {}), "pipeline_id": pipeline_id}
    safe_set_pipeline_id(pipeline_id)
    state.mark_started(node_name)
    timeout_seconds = _node_timeout_seconds(node_name)
    started_at = time.perf_counter()
    logger.info("Node started.", node=node_name, job_id=state.job_id, url=state.url, pipeline_id=pipeline_id)
    _append_node_run_log(
        state,
        event="node_started",
        message=f"{node_name.title()} node started.",
        details={
            "node": node_name,
            "pipeline_id": pipeline_id,
            "timeout_seconds": timeout_seconds,
        },
    )
    try:
        updated_state = await asyncio.wait_for(operation(), timeout=timeout_seconds)
        updated_state.config = {**(updated_state.config or {}), "pipeline_id": pipeline_id}
        elapsed = round(time.perf_counter() - started_at, 6)
        updated_state.node_timings[node_name] = elapsed
        _append_node_run_log(
            updated_state,
            event="node_completed",
            message=f"{node_name.title()} node completed.",
            details={
                "node": node_name,
                "pipeline_id": pipeline_id,
                "execution_time_seconds": elapsed,
                "status": updated_state.status,
            },
        )
        logger.info(
            "Node completed.",
            node=node_name,
            job_id=updated_state.job_id,
            status=updated_state.status,
            execution_time=elapsed,
            errors=updated_state.errors,
            pipeline_id=pipeline_id,
        )
        return updated_state
    except asyncio.TimeoutError:
        elapsed = round(time.perf_counter() - started_at, 6)
        state.node_timings[node_name] = elapsed
        message = f"{node_name} timed out after {timeout_seconds} seconds"
        _halt_pipeline(state, reason=message, node_name=node_name)
        _append_node_run_log(
            state,
            event="node_timeout",
            message=message,
            level="error",
            details={
                "node": node_name,
                "pipeline_id": pipeline_id,
                "execution_time_seconds": elapsed,
                "timeout_seconds": timeout_seconds,
            },
        )
        logger.error(
            "Node timed out.",
            node=node_name,
            job_id=state.job_id,
            execution_time=elapsed,
            timeout_seconds=timeout_seconds,
            pipeline_id=pipeline_id,
        )
        return state
    except Exception as exc:
        elapsed = round(time.perf_counter() - started_at, 6)
        state.node_timings[node_name] = elapsed
        message = f"{node_name} failed: {exc}"
        _halt_pipeline(state, reason=message, node_name=node_name)
        _append_node_run_log(
            state,
            event="node_failed",
            message=message,
            level="error",
            details={
                "node": node_name,
                "pipeline_id": pipeline_id,
                "execution_time_seconds": elapsed,
                "error": str(exc),
            },
        )
        logger.error(
            "Node failed.",
            node=node_name,
            job_id=state.job_id,
            execution_time=elapsed,
            error=str(exc),
            exc_info=True,
            pipeline_id=pipeline_id,
        )
        return state


async def intake_node(state: WorkflowState) -> WorkflowState:
    async def operation() -> WorkflowState:
        intake_agent = _create_intake_agent()
        result = await intake_agent.safe_execute(
            {
                "url": state.url,
                "scrape_type": state.scraping_type,
                "credentials": state.credentials,
                "config": state.config,
                "providers": (state.credentials or {}).get("providers", {}),
                "pipeline_id": (state.config or {}).get("pipeline_id"),
            }
        )
        if result["status"] == "success":
            payload = result.get("data", {})
            state.strategy = _merge_strategy(payload.get("strategy", {}), state.strategy)
            state.config = payload.get("config", state.config)
        else:
            state.add_error(f"Intake failed: {result.get('error', 'Unknown error')}")
            state.status = "failed"
        return state

    return await _run_logged_node(state, "intake", operation)


async def scraper_node(state: WorkflowState) -> WorkflowState:
    async def operation() -> WorkflowState:
        scraper_agent = _create_scraper_agent()
        try:
            result = await scraper_agent.safe_execute(
                {
                    "url": state.url,
                    "credentials": state.credentials,
                    "strategy": state.strategy,
                    "config": state.config,
                    "providers": (state.credentials or {}).get("providers", {}),
                    "run_id": state.run_id or state.job_id or "pipeline",
                    "pipeline_id": (state.config or {}).get("pipeline_id"),
                }
            )
            if result["status"] == "success":
                state.raw_data = result.get("data", {})
            else:
                state.add_error(f"Scraper failed: {result.get('error', 'Unknown error')}")
                state.status = "failed"
        finally:
            await scraper_agent.browser_manager.close()
        return state

    return await _run_logged_node(state, "scraper", operation)


async def processing_node(state: WorkflowState) -> WorkflowState:
    async def operation() -> WorkflowState:
        processing_agent = _create_processing_agent()
        raw_data = state.raw_data or {}
        raw_pages = raw_data.get("pages", []) if isinstance(raw_data.get("pages"), list) else []
        page_sources = [
            page for page in raw_pages
            if isinstance(page, dict) and page.get("html_path")
        ]
        if not page_sources and raw_data.get("html_path"):
            page_sources = [
                {
                    "html_path": raw_data.get("html_path"),
                    "final_url": raw_data.get("final_url") or state.url,
                }
            ]

        final_url = raw_data.get("final_url") or state.url
        if not page_sources:
            state.add_error("Processing failed: missing html_path from scraper output.")
            state.status = "failed"
            return state

        extracted_payloads: list[dict[str, Any]] = []
        semantic_markdown_sections: list[str] = []
        markdown_char_budget = 120_000
        markdown_char_count = 0
        raw_html_total_bytes = 0
        for page in page_sources:
            raw_html = storage_manager.get_file_text(page["html_path"])
            raw_html_total_bytes += len(raw_html.encode("utf-8"))
            semantic_markdown = html_to_semantic_markdown(raw_html, max_chars=40_000)
            if semantic_markdown and markdown_char_count < markdown_char_budget:
                page_label = str(page.get("final_url") or final_url or "").strip()
                section = (
                    f"## {page_label}\n\n{semantic_markdown}"
                    if len(page_sources) > 1
                    else semantic_markdown
                )
                semantic_markdown_sections.append(section)
                markdown_char_count += len(section)
            extracted_payloads.append(
                extractor.extract(
                    raw_html=raw_html,
                    url=page.get("final_url") or final_url,
                    scraping_type=state.scraping_type,
                    selectors=(state.strategy or {}).get("selectors"),
                )
            )

        extracted = _aggregate_extracted_payloads(
            extracted_payloads,
            source_url=final_url,
            scraping_type=state.scraping_type,
        )
        semantic_markdown_payload = "\n\n".join(semantic_markdown_sections)
        markdown_total_bytes = len(semantic_markdown_payload.encode("utf-8")) if semantic_markdown_payload else 0
        state.token_compression_ratio = (
            round(markdown_total_bytes / raw_html_total_bytes, 6) if raw_html_total_bytes > 0 else None
        )
        state.stealth_engaged = bool((state.config or {}).get("stealth_mode", False))
        run_reference = str(state.run_id or state.job_id or "").strip()
        if run_reference and semantic_markdown_payload:
            state.markdown_snapshot_path = storage_manager.save_markdown_snapshot(
                run_reference,
                semantic_markdown_payload,
            )
        else:
            state.markdown_snapshot_path = ""
        result = await processing_agent.safe_execute(
            {
                "extracted": extracted,
                "semantic_markdown": semantic_markdown_payload,
                "url": final_url,
                "context": str((state.config or {}).get("prompt") or ""),
                "providers": (state.credentials or {}).get("providers", {}),
                "pipeline_id": (state.config or {}).get("pipeline_id"),
            }
        )
        if result["status"] == "success":
            state.processed_data = result.get("data", {})
        else:
            state.add_error(f"Processing failed: {result.get('error', 'Unknown error')}")
            state.status = "failed"
        return state

    return await _run_logged_node(state, "processing", operation)


async def vector_node(state: WorkflowState) -> WorkflowState:
    async def operation() -> WorkflowState:
        items = state.processed_data.get("items", [])
        if not items:
            state.vector_data = {
                "status": "skipped",
                "optional": True,
                "reason": "no_items",
                "embeddings_generated": 0,
                "embeddings": [],
            }
            return state

        try:
            vector_agent = _create_vector_agent()
        except Exception as exc:
            state.add_error(f"Vector unavailable: {exc}")
            state.vector_data = {
                "status": "failed",
                "optional": True,
                "reason": str(exc),
                "embeddings_generated": 0,
                "embeddings": [],
            }
            return state

        embed_result = await vector_agent.safe_execute(
            {
                "operation": "embed",
                "items": items,
                "providers": (state.credentials or {}).get("providers", {}),
                "context": str((state.config or {}).get("prompt") or ""),
                "pipeline_id": (state.config or {}).get("pipeline_id"),
            }
        )
        if embed_result["status"] != "success":
            state.add_error(f"Vector embedding failed: {embed_result.get('error', 'Unknown error')}")
            state.vector_data = {
                "status": "failed",
                "optional": True,
                "reason": embed_result.get("error", "Unknown error"),
                "embeddings_generated": 0,
                "embeddings": [],
            }
            return state

        embeddings = embed_result.get("data", {})
        state.vector_data = embeddings
        embedding_items = embeddings.get("embeddings", [])
        if not embedding_items:
            logger.warning(
                "Skipping vector indexing because no embeddings were produced.",
                node="vector",
                job_id=state.job_id,
            )
            state.vector_data["status"] = "skipped"
            state.vector_data["optional"] = True
            return state

        index_result = await vector_agent.safe_execute(
            {
                "operation": "index",
                "items": embedding_items,
                "user_id": state.user_id,
                "pipeline_id": (state.config or {}).get("pipeline_id"),
            }
        )
        if index_result["status"] != "success":
            state.add_error(f"Vector indexing failed: {index_result.get('error', 'Unknown error')}")
            state.vector_data["status"] = "failed"
            state.vector_data["optional"] = True
            state.vector_data["index_error"] = index_result.get("error", "Unknown error")
        else:
            state.vector_data["index"] = index_result.get("data", {})
            state.vector_data["status"] = "success"
            state.vector_data["optional"] = True
        return state

    return await _run_logged_node(state, "vector", operation)


async def analysis_node(state: WorkflowState) -> WorkflowState:
    async def operation() -> WorkflowState:
        items = state.processed_data.get("items", [])
        if not items:
            state.analysis_data = {
                "status": "skipped",
                "optional": True,
                "reason": "no_items",
            }
            return state

        analysis_agent = _create_analysis_agent()
        result = await analysis_agent.safe_execute(
            {
                "items": items,
                "analysis_type": "both",
                "context": str((state.config or {}).get("prompt") or ""),
                "providers": (state.credentials or {}).get("providers", {}),
                "pipeline_id": (state.config or {}).get("pipeline_id"),
            }
        )
        if result["status"] == "success":
            state.analysis_data = {
                "status": "success",
                "optional": True,
                **result.get("data", {}),
            }
        else:
            state.add_error(f"Analysis failed: {result.get('error', 'Unknown error')}")
            state.analysis_data = {
                "status": "failed",
                "optional": True,
                "reason": result.get("error", "Unknown error"),
            }
        return state

    return await _run_logged_node(state, "analysis", operation)


async def export_node(state: WorkflowState) -> WorkflowState:
    async def operation() -> WorkflowState:
        if not state.processed_data:
            state.export_paths = {}
            state.status = "failed"
            state.add_error("Export failed: missing processed data.")
            return state

        export_agent = _create_export_agent()
        result = await export_agent.safe_execute(
            {
                "processed": {
                    "status": "success",
                    "data": state.processed_data,
                    "metadata": {"source_url": state.raw_data.get("final_url") or state.url},
                },
                "analysis": state.analysis_data,
                "context": str((state.config or {}).get("prompt") or ""),
                "providers": (state.credentials or {}).get("providers", {}),
                "export_id": state.run_id or state.job_id or None,
                "source_url": state.raw_data.get("final_url") or state.url,
                "title": state.processed_data.get("summary", "")[:80] or "Processed Web Data Export",
                "pipeline_id": (state.config or {}).get("pipeline_id"),
            }
        )
        if result["status"] == "success":
            state.export_paths = result.get("data", {})
            if state.status != "failed":
                state.status = "completed"
        else:
            state.add_error(f"Export failed: {result.get('error', 'Unknown error')}")
            state.export_paths = {}
            state.status = "completed" if state.processed_data else "failed"
        state.mark_finished()
        return state

    return await _run_logged_node(state, "export", operation)


def route_after_intake(state: WorkflowState) -> str:
    return "end" if _should_end(state) else "scraper"


def route_after_scraper(state: WorkflowState) -> str:
    return "end" if _should_end(state) else "processing"


def route_after_processing(state: WorkflowState) -> str:
    return "end" if _should_end(state) else "vector"


def route_after_vector(state: WorkflowState) -> str:
    return "end" if _should_end(state) else "analysis"


def route_after_analysis(state: WorkflowState) -> str:
    return "end" if _should_end(state) else "export"

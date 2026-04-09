from __future__ import annotations

from typing import Any

from langgraph.graph import END, StateGraph

from app.core.logging import get_logger
from app.core.logger import clear_pipeline_id, set_pipeline_id
from app.orchestrator.nodes import (
    analysis_node,
    export_node,
    intake_node,
    processing_node,
    route_after_analysis,
    route_after_intake,
    route_after_processing,
    route_after_scraper,
    route_after_vector,
    scraper_node,
    vector_node,
)
from app.orchestrator.state import WorkflowState


logger = get_logger("app.orchestrator.graph")


def _build_initial_strategy(input_data: dict[str, Any]) -> dict[str, Any]:
    strategy = input_data.get("strategy")
    if not isinstance(strategy, dict):
        return {}
    return dict(strategy)


def create_pipeline() -> Any:
    workflow = StateGraph(WorkflowState)
    workflow.add_node("intake", intake_node)
    workflow.add_node("scraper", scraper_node)
    workflow.add_node("processing", processing_node)
    workflow.add_node("vector", vector_node)
    workflow.add_node("analysis", analysis_node)
    workflow.add_node("export", export_node)

    workflow.set_entry_point("intake")
    workflow.add_conditional_edges("intake", route_after_intake, {"scraper": "scraper", "end": END})
    workflow.add_conditional_edges("scraper", route_after_scraper, {"processing": "processing", "end": END})
    workflow.add_conditional_edges("processing", route_after_processing, {"vector": "vector", "end": END})
    workflow.add_conditional_edges("vector", route_after_vector, {"analysis": "analysis", "end": END})
    workflow.add_conditional_edges("analysis", route_after_analysis, {"export": "export", "end": END})
    workflow.add_edge("export", END)
    return workflow.compile()


pipeline = create_pipeline()


def _coerce_state(result: Any) -> WorkflowState:
    if isinstance(result, WorkflowState):
        return result
    if isinstance(result, dict):
        return WorkflowState(**result)
    raise TypeError(f"Unexpected pipeline result type: {type(result).__name__}")


async def _run_pipeline_sequential(initial_state: WorkflowState) -> WorkflowState:
    state = await intake_node(initial_state)
    if route_after_intake(state) == "end":
        return state

    state = await scraper_node(state)
    if route_after_scraper(state) == "end":
        return state

    state = await processing_node(state)
    if route_after_processing(state) == "end":
        return state

    state = await vector_node(state)
    if route_after_vector(state) == "end":
        return state

    state = await analysis_node(state)
    if route_after_analysis(state) == "end":
        return state

    return await export_node(state)


async def run_pipeline(input_data: dict[str, Any]) -> dict[str, Any]:
    initial_state = WorkflowState(
        job_id=str(input_data.get("job_id", "")),
        url=str(input_data.get("url", "")),
        scraping_type=str(input_data.get("scraping_type", input_data.get("scrape_type", "general"))),
        credentials=input_data.get("credentials") or {},
        config=input_data.get("config") or {},
        strategy=_build_initial_strategy(input_data),
        user_id=str(input_data.get("user_id", "")),
        run_id=str(input_data.get("run_id", "")),
        status="pending",
    )
    logger.info("Pipeline invocation started.", job_id=initial_state.job_id, url=initial_state.url)
    set_pipeline_id(initial_state.run_id or initial_state.job_id or initial_state.url)
    try:
        final_state = _coerce_state(await _run_pipeline_sequential(initial_state))
    finally:
        clear_pipeline_id()
    if final_state.status not in {"completed", "failed"}:
        final_state.status = "completed" if final_state.processed_data else "failed"
    if not final_state.finished_at:
        final_state.mark_finished()
    result = final_state.to_dict()
    logger.info(
        "Pipeline invocation finished.",
        job_id=final_state.job_id,
        status=final_state.status,
        errors=final_state.errors,
        export_paths=final_state.export_paths,
    )
    return result


async def run_scraping_workflow(
    job_id: Any,
    run_id: Any,
    user_id: Any,
    url: str,
    scrape_type: str = "general",
    credentials: dict[str, Any] | None = None,
    config: dict[str, Any] | None = None,
    export_format: str | None = None,
    strategy: dict[str, Any] | None = None,
) -> WorkflowState:
    final_state = _coerce_state(
        await _run_pipeline_sequential(
            WorkflowState(
            job_id=str(job_id),
            run_id=str(run_id),
            user_id=str(user_id),
            url=url,
            scraping_type=scrape_type,
            credentials=credentials or {},
            config={**(config or {}), **({"export_format": export_format} if export_format else {})},
            strategy=_build_initial_strategy({"strategy": strategy}),
        )
        )
    )
    if final_state.status not in {"completed", "failed"}:
        final_state.status = "completed" if final_state.processed_data else "failed"
    if not final_state.finished_at:
        final_state.mark_finished()
    return final_state

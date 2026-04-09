"""LangGraph workflow orchestration package.

Keep package exports lazy so lightweight imports such as
``app.orchestrator.memory_service`` do not require the full AI stack.
"""

from importlib import import_module


__all__ = [
    "SmartOrchestrator",
    "decision_layer",
    "run_pipeline",
    "run_scraping_workflow",
]


def __getattr__(name: str):
    if name in {"run_pipeline", "run_scraping_workflow"}:
        module = import_module("app.orchestrator.graph")
        return getattr(module, name)

    if name in {"SmartOrchestrator", "decision_layer"}:
        module = import_module("app.orchestrator.smart_orchestrator")
        return getattr(module, name)

    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

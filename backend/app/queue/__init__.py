"""Async job processing package using Celery with Redis broker.

Keep task and callback exports lazy so importing ``app.queue`` for
``celery_app`` does not require the full worker dependency stack.
"""

from importlib import import_module

from app.queue.celery_app import celery_app

__all__ = [
    "celery_app",
    "ping",
    "basic_async_task",
    "run_scraping_job",
    "run_export",
    "generate_export",
    "run_analysis",
    "on_task_success",
    "on_task_failure",
    "on_task_retry",
    "on_task_revoked",
    "on_task_started",
]


def __getattr__(name: str):
    task_exports = {
        "ping",
        "basic_async_task",
        "run_scraping_job",
        "run_export",
        "generate_export",
        "run_analysis",
    }
    callback_exports = {
        "on_task_success",
        "on_task_failure",
        "on_task_retry",
        "on_task_revoked",
        "on_task_started",
    }

    if name in task_exports:
        module = import_module("app.queue.tasks")
        return getattr(module, name)

    if name in callback_exports:
        module = import_module("app.queue.callbacks")
        return getattr(module, name)

    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

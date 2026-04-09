from app.core import logging as logging_module
from app.core.logging import *  # noqa: F401,F403


def get_request_id() -> str:
    try:
        return logging_module._REQUEST_ID.get()
    except Exception:
        return ""


def get_pipeline_id() -> str:
    try:
        return logging_module._PIPELINE_ID.get()
    except Exception:
        return ""


def safe_set_request_id(request_id: str) -> None:
    try:
        logging_module.set_request_id(request_id)
    except Exception:
        return


def safe_clear_request_id() -> None:
    try:
        logging_module.clear_request_id()
    except Exception:
        return


def safe_set_pipeline_id(pipeline_id: str) -> None:
    try:
        logging_module.set_pipeline_id(pipeline_id)
    except Exception:
        return


def safe_clear_pipeline_id() -> None:
    try:
        logging_module.clear_pipeline_id()
    except Exception:
        return


def get_trace_context() -> dict[str, str]:
    return {
        "request_id": get_request_id(),
        "pipeline_id": get_pipeline_id(),
    }

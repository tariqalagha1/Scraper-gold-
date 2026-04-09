"""Celery task callbacks for handling completion and failure events.

Provides callback functions that are invoked when tasks complete
successfully, fail, or are retried. These callbacks handle logging
and can be extended for notifications or cleanup.
"""
from typing import Any, Optional

from app.core.logging import get_agent_logger

logger = get_agent_logger("queue.callbacks")


def on_task_success(task_id: str, result: Any, task_name: str) -> None:
    """Handle successful task completion.
    
    Called when a Celery task completes successfully.
    Logs the completion and can be extended for notifications.
    
    Args:
        task_id: Unique identifier of the completed task
        result: Return value from the task
        task_name: Name of the task that completed
    """
    logger.info(
        f"Task {task_name} [{task_id}] completed successfully",
        extra={
            "task_id": task_id,
            "task_name": task_name,
            "result": _summarize_result(result)
        }
    )


def on_task_failure(task_id: str, exception: Exception, task_name: str) -> None:
    """Handle task failure.
    
    Called when a Celery task fails after exhausting retries.
    Logs the failure details for debugging.
    
    Args:
        task_id: Unique identifier of the failed task
        exception: The exception that caused the failure
        task_name: Name of the task that failed
    """
    logger.error(
        f"Task {task_name} [{task_id}] failed: {exception}",
        extra={
            "task_id": task_id,
            "task_name": task_name,
            "error": str(exception),
            "error_type": type(exception).__name__
        }
    )


def on_task_retry(task_id: str, exception: Exception, task_name: str, retry_count: int) -> None:
    """Handle task retry.
    
    Called when a Celery task is scheduled for retry after a failure.
    Logs the retry attempt for monitoring.
    
    Args:
        task_id: Unique identifier of the retrying task
        exception: The exception that triggered the retry
        task_name: Name of the task being retried
        retry_count: Current retry attempt number
    """
    logger.warning(
        f"Task {task_name} [{task_id}] retrying (attempt {retry_count}): {exception}",
        extra={
            "task_id": task_id,
            "task_name": task_name,
            "retry_count": retry_count,
            "error": str(exception)
        }
    )


def on_task_revoked(task_id: str, task_name: str, terminated: bool, signum: Optional[int]) -> None:
    """Handle task revocation.
    
    Called when a Celery task is revoked/cancelled.
    
    Args:
        task_id: Unique identifier of the revoked task
        task_name: Name of the task that was revoked
        terminated: Whether the task was terminated
        signum: Signal number if terminated
    """
    logger.warning(
        f"Task {task_name} [{task_id}] was revoked",
        extra={
            "task_id": task_id,
            "task_name": task_name,
            "terminated": terminated,
            "signum": signum
        }
    )


def on_task_started(task_id: str, task_name: str, args: tuple, kwargs: dict) -> None:
    """Handle task start.
    
    Called when a Celery task begins execution.
    
    Args:
        task_id: Unique identifier of the starting task
        task_name: Name of the task starting
        args: Positional arguments passed to the task
        kwargs: Keyword arguments passed to the task
    """
    logger.info(
        f"Task {task_name} [{task_id}] started",
        extra={
            "task_id": task_id,
            "task_name": task_name,
            "args": _summarize_result(args),
            "kwargs": _summarize_result(kwargs)
        }
    )


def _summarize_result(result: Any, max_length: int = 200) -> str:
    """Create a truncated string summary of a result for logging.
    
    Args:
        result: Result to summarize
        max_length: Maximum length of the summary
        
    Returns:
        Truncated string representation
    """
    try:
        text = str(result)
        return text[:max_length] + "..." if len(text) > max_length else text
    except Exception:
        return "<unserializable>"

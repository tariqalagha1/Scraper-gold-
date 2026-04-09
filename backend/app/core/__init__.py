"""Core utilities for the Smart Scraper Platform.

This module exports core utilities including logging, exceptions,
retry logic, and security functions.
"""
from app.core.exceptions import (
    AgentError,
    AgentExecutionError,
    AuthenticationError,
    AuthorizationError,
    ConfigurationError,
    DatabaseError,
    ExportError,
    ExtractionError,
    LoginError,
    ProcessingError,
    QueueError,
    RateLimitError,
    RobotsBlockedError,
    ScraperBaseException,
    ScrapingError,
    ValidationError,
    VectorError,
    register_exception_handlers,
)
from app.core.logging import (
    AgentLogHandler,
    JSONFormatter,
    StructuredLogger,
    async_timed_operation,
    get_agent_logger,
    get_logger,
    log_execution_time,
    timed_operation,
)
from app.core.retry import RetryConfig, RetryContext, retry, retry_with_config
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_access_token,
    get_token_payload,
    hash_password,
    verify_password,
)

__all__ = [
    # Logging
    "get_logger",
    "get_agent_logger",
    "StructuredLogger",
    "JSONFormatter",
    "AgentLogHandler",
    "timed_operation",
    "async_timed_operation",
    "log_execution_time",
    # Exceptions
    "ScraperBaseException",
    "ConfigurationError",
    "DatabaseError",
    "AuthenticationError",
    "AuthorizationError",
    "ScrapingError",
    "ExtractionError",
    "LoginError",
    "RateLimitError",
    "RobotsBlockedError",
    "ProcessingError",
    "ExportError",
    "VectorError",
    "QueueError",
    "AgentError",
    "AgentExecutionError",
    "ValidationError",
    "register_exception_handlers",
    # Retry
    "retry",
    "retry_with_config",
    "RetryConfig",
    "RetryContext",
    # Security
    "hash_password",
    "verify_password",
    "create_access_token",
    "create_refresh_token",
    "decode_access_token",
    "get_token_payload",
]

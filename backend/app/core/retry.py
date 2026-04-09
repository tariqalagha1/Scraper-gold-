"""Retry logic with exponential backoff for the Smart Scraper Platform.

Provides a flexible retry decorator that works with both sync and async
functions, supporting configurable retry counts, delays, and callbacks.
"""
import asyncio
import functools
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Optional, Tuple, Type, TypeVar, Union

from app.core.logging import get_logger

logger = get_logger(__name__)

F = TypeVar("F", bound=Callable[..., Any])


@dataclass
class RetryConfig:
    """Configuration for retry behavior.
    
    Attributes:
        max_retries: Maximum number of retry attempts.
        delay: Initial delay between retries in seconds.
        backoff_factor: Multiplier for delay after each retry.
        exceptions: Tuple of exception types to catch and retry on.
        on_retry: Optional callback function called on each retry.
        max_delay: Maximum delay between retries (caps exponential growth).
        jitter: Whether to add random jitter to delays.
    """
    max_retries: int = 3
    delay: float = 1.0
    backoff_factor: float = 2.0
    exceptions: Tuple[Type[Exception], ...] = field(default_factory=lambda: (Exception,))
    on_retry: Optional[Callable[[int, Exception, float], None]] = None
    max_delay: float = 60.0
    jitter: bool = False

    def calculate_delay(self, attempt: int) -> float:
        """Calculate delay for a given attempt number.
        
        Args:
            attempt: The current retry attempt number (0-indexed).
            
        Returns:
            Delay in seconds for this attempt.
        """
        delay = self.delay * (self.backoff_factor ** attempt)
        delay = min(delay, self.max_delay)
        
        if self.jitter:
            import random
            delay = delay * (0.5 + random.random())
            
        return delay


def retry(
    max_retries: int = 3,
    delay: float = 1.0,
    backoff_factor: float = 2.0,
    exceptions: Tuple[Type[Exception], ...] = (Exception,),
    on_retry: Optional[Callable[[int, Exception, float], None]] = None,
    max_delay: float = 60.0,
    jitter: bool = False,
) -> Callable[[F], F]:
    """Decorator for retrying functions with exponential backoff.
    
    Works with both synchronous and asynchronous functions.
    
    Args:
        max_retries: Maximum number of retry attempts. Default 3.
        delay: Initial delay between retries in seconds. Default 1.0.
        backoff_factor: Multiplier for delay after each retry. Default 2.0.
        exceptions: Tuple of exception types to catch and retry. Default (Exception,).
        on_retry: Optional callback(attempt, exception, next_delay) called on each retry.
        max_delay: Maximum delay between retries. Default 60.0.
        jitter: Whether to add random jitter to delays. Default False.
        
    Returns:
        Decorated function with retry logic.
        
    Example:
        @retry(max_retries=5, delay=0.5, exceptions=(ConnectionError, TimeoutError))
        async def fetch_data(url: str) -> dict:
            async with httpx.AsyncClient() as client:
                response = await client.get(url)
                return response.json()
    """
    config = RetryConfig(
        max_retries=max_retries,
        delay=delay,
        backoff_factor=backoff_factor,
        exceptions=exceptions,
        on_retry=on_retry,
        max_delay=max_delay,
        jitter=jitter,
    )
    
    def decorator(func: F) -> F:
        if asyncio.iscoroutinefunction(func):
            @functools.wraps(func)
            async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
                last_exception: Optional[Exception] = None
                
                for attempt in range(config.max_retries + 1):
                    try:
                        return await func(*args, **kwargs)
                    except config.exceptions as e:
                        last_exception = e
                        
                        if attempt < config.max_retries:
                            next_delay = config.calculate_delay(attempt)
                            
                            logger.warning(
                                f"Retry attempt {attempt + 1}/{config.max_retries} "
                                f"for {func.__name__} after error: {e}",
                                action="retry",
                                extra={
                                    "attempt": attempt + 1,
                                    "max_retries": config.max_retries,
                                    "error": str(e),
                                    "next_delay": next_delay,
                                    "function": func.__name__,
                                },
                            )
                            
                            if config.on_retry:
                                config.on_retry(attempt + 1, e, next_delay)
                            
                            await asyncio.sleep(next_delay)
                        else:
                            logger.error(
                                f"All {config.max_retries} retries exhausted for {func.__name__}",
                                action="retry_exhausted",
                                error_data=str(e),
                                extra={
                                    "function": func.__name__,
                                    "total_attempts": config.max_retries + 1,
                                },
                            )
                
                # All retries exhausted, raise the last exception
                if last_exception is not None:
                    raise last_exception
                    
            return async_wrapper  # type: ignore
        else:
            @functools.wraps(func)
            def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
                last_exception: Optional[Exception] = None
                
                for attempt in range(config.max_retries + 1):
                    try:
                        return func(*args, **kwargs)
                    except config.exceptions as e:
                        last_exception = e
                        
                        if attempt < config.max_retries:
                            next_delay = config.calculate_delay(attempt)
                            
                            logger.warning(
                                f"Retry attempt {attempt + 1}/{config.max_retries} "
                                f"for {func.__name__} after error: {e}",
                                action="retry",
                                extra={
                                    "attempt": attempt + 1,
                                    "max_retries": config.max_retries,
                                    "error": str(e),
                                    "next_delay": next_delay,
                                    "function": func.__name__,
                                },
                            )
                            
                            if config.on_retry:
                                config.on_retry(attempt + 1, e, next_delay)
                            
                            time.sleep(next_delay)
                        else:
                            logger.error(
                                f"All {config.max_retries} retries exhausted for {func.__name__}",
                                action="retry_exhausted",
                                error_data=str(e),
                                extra={
                                    "function": func.__name__,
                                    "total_attempts": config.max_retries + 1,
                                },
                            )
                
                # All retries exhausted, raise the last exception
                if last_exception is not None:
                    raise last_exception
                    
            return sync_wrapper  # type: ignore

    return decorator


def retry_with_config(config: RetryConfig) -> Callable[[F], F]:
    """Create a retry decorator from a RetryConfig object.
    
    Args:
        config: RetryConfig instance with retry settings.
        
    Returns:
        Retry decorator configured with the provided settings.
        
    Example:
        config = RetryConfig(max_retries=5, delay=2.0)
        
        @retry_with_config(config)
        async def unreliable_operation():
            ...
    """
    return retry(
        max_retries=config.max_retries,
        delay=config.delay,
        backoff_factor=config.backoff_factor,
        exceptions=config.exceptions,
        on_retry=config.on_retry,
        max_delay=config.max_delay,
        jitter=config.jitter,
    )


class RetryContext:
    """Context manager for manual retry control.
    
    Useful when you need more fine-grained control over retry behavior
    than the decorator provides.
    
    Example:
        async with RetryContext(max_retries=3) as ctx:
            while ctx.should_retry():
                try:
                    result = await risky_operation()
                    ctx.success()
                    break
                except Exception as e:
                    await ctx.handle_error(e)
    """

    def __init__(
        self,
        max_retries: int = 3,
        delay: float = 1.0,
        backoff_factor: float = 2.0,
        exceptions: Tuple[Type[Exception], ...] = (Exception,),
    ) -> None:
        """Initialize retry context.
        
        Args:
            max_retries: Maximum number of retry attempts.
            delay: Initial delay between retries.
            backoff_factor: Multiplier for delay after each retry.
            exceptions: Exception types to catch.
        """
        self.config = RetryConfig(
            max_retries=max_retries,
            delay=delay,
            backoff_factor=backoff_factor,
            exceptions=exceptions,
        )
        self._attempt = 0
        self._succeeded = False
        self._last_exception: Optional[Exception] = None

    async def __aenter__(self) -> "RetryContext":
        """Enter async context."""
        return self

    async def __aexit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc_val: Optional[BaseException],
        exc_tb: Any,
    ) -> bool:
        """Exit async context."""
        if exc_val is not None and not self._succeeded:
            if self._last_exception is not None:
                raise self._last_exception
        return False

    def __enter__(self) -> "RetryContext":
        """Enter sync context."""
        return self

    def __exit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc_val: Optional[BaseException],
        exc_tb: Any,
    ) -> bool:
        """Exit sync context."""
        if exc_val is not None and not self._succeeded:
            if self._last_exception is not None:
                raise self._last_exception
        return False

    def should_retry(self) -> bool:
        """Check if another retry attempt should be made.
        
        Returns:
            True if more retries are available.
        """
        return self._attempt <= self.config.max_retries and not self._succeeded

    def success(self) -> None:
        """Mark the operation as successful."""
        self._succeeded = True

    @property
    def attempt(self) -> int:
        """Get current attempt number (1-indexed)."""
        return self._attempt

    async def handle_error_async(self, error: Exception) -> None:
        """Handle an error in async context.
        
        Args:
            error: The exception that occurred.
            
        Raises:
            Exception: Re-raises if retries are exhausted.
        """
        if not isinstance(error, self.config.exceptions):
            raise error
            
        self._last_exception = error
        self._attempt += 1
        
        if self._attempt <= self.config.max_retries:
            delay = self.config.calculate_delay(self._attempt - 1)
            logger.warning(
                f"Retry attempt {self._attempt}/{self.config.max_retries} after error: {error}",
                action="retry",
                extra={"attempt": self._attempt, "error": str(error)},
            )
            await asyncio.sleep(delay)
        else:
            raise error

    def handle_error_sync(self, error: Exception) -> None:
        """Handle an error in sync context.
        
        Args:
            error: The exception that occurred.
            
        Raises:
            Exception: Re-raises if retries are exhausted.
        """
        if not isinstance(error, self.config.exceptions):
            raise error
            
        self._last_exception = error
        self._attempt += 1
        
        if self._attempt <= self.config.max_retries:
            delay = self.config.calculate_delay(self._attempt - 1)
            logger.warning(
                f"Retry attempt {self._attempt}/{self.config.max_retries} after error: {error}",
                action="retry",
                extra={"attempt": self._attempt, "error": str(error)},
            )
            time.sleep(delay)
        else:
            raise error

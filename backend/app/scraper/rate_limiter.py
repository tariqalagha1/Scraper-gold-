"""Rate limiting implementation.

Per AGENT_RULES.md: Respect rate limits.
"""
import asyncio
import time
from typing import Optional

from app.config import settings


class RateLimiter:
    """Implements rate limiting for scraping requests.
    
    Per AGENT_RULES.md: Respect rate limits.
    """
    
    def __init__(self, delay: Optional[float] = None):
        """Initialize the rate limiter.
        
        Args:
            delay: Delay in seconds between requests
        """
        self._delay = delay or settings.DEFAULT_RATE_LIMIT_DELAY
        self._last_request_time: float = 0
    
    def set_delay(self, delay: float) -> None:
        """Set the delay between requests.
        
        Args:
            delay: Delay in seconds
        """
        self._delay = max(0, delay)
    
    async def wait(self) -> None:
        """Wait until rate limit allows next request.
        
        Ensures minimum delay between consecutive requests.
        """
        if self._delay <= 0:
            return
        
        current_time = time.time()
        elapsed = current_time - self._last_request_time
        
        if elapsed < self._delay:
            wait_time = self._delay - elapsed
            await asyncio.sleep(wait_time)
        
        self._last_request_time = time.time()
    
    def reset(self) -> None:
        """Reset the rate limiter state."""
        self._last_request_time = 0

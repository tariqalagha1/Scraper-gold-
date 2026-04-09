"""Pagination and navigation handler."""
from typing import Optional
import logging
from urllib.parse import urljoin

from playwright.async_api import Page, TimeoutError as PlaywrightTimeoutError


logger = logging.getLogger(__name__)


class PageNavigator:
    """Handles pagination and navigation during scraping.
    
    Supports various pagination patterns:
    - Next button pagination
    - Page number pagination
    - Infinite scroll
    - Load more buttons
    """
    
    NEXT_BUTTON_SELECTORS = [
        'a:has-text("Next")',
        'button:has-text("Next")',
        'a.next',
        'button.next',
        '.pagination a.next',
        '.pagination .next a',
        '[rel="next"]',
        'a[aria-label="Next"]',
        'button[aria-label="Next"]',
    ]
    
    LOAD_MORE_SELECTORS = [
        'button:has-text("Load more")',
        'button:has-text("Show more")',
        'a:has-text("Load more")',
        '.load-more',
        '#load-more',
    ]
    
    async def get_next_page(
        self,
        page: Page,
        pagination_type: str = "auto",
        wait_for_selector: str | None = None,
        wait_timeout_ms: int | None = None,
    ) -> Optional[str]:
        """Get the URL of the next page.
        
        Args:
            page: Playwright page instance
            pagination_type: Type of pagination (auto, next, number, scroll, load_more)
            
        Returns:
            URL of next page, or None if no more pages
        """
        if pagination_type == "auto":
            # Try different pagination methods
            url = await self._try_next_button(
                page,
                wait_for_selector=wait_for_selector,
                wait_timeout_ms=wait_timeout_ms,
            )
            if url:
                return url
            
            url = await self._try_load_more(
                page,
                wait_for_selector=wait_for_selector,
                wait_timeout_ms=wait_timeout_ms,
            )
            if url:
                return url
            
            return None
        
        elif pagination_type == "next":
            return await self._try_next_button(
                page,
                wait_for_selector=wait_for_selector,
                wait_timeout_ms=wait_timeout_ms,
            )
        
        elif pagination_type == "load_more":
            return await self._try_load_more(
                page,
                wait_for_selector=wait_for_selector,
                wait_timeout_ms=wait_timeout_ms,
            )
        
        elif pagination_type == "scroll":
            return await self._try_infinite_scroll(page)
        
        return None
    
    async def _try_next_button(
        self,
        page: Page,
        *,
        wait_for_selector: str | None = None,
        wait_timeout_ms: int | None = None,
    ) -> Optional[str]:
        """Try to find and use next button pagination.
        
        Args:
            page: Playwright page instance
            
        Returns:
            URL of next page, or None
        """
        for selector in self.NEXT_BUTTON_SELECTORS:
            try:
                element = page.locator(selector).first
                if await element.count() > 0:
                    # Check if it's a link with href
                    href = await element.get_attribute("href")
                    if href:
                        return urljoin(page.url, href)
                    else:
                        # It's a button, click it and return current page
                        await element.click()
                        await self._settle_after_interaction(
                            page,
                            wait_for_selector=wait_for_selector,
                            wait_timeout_ms=wait_timeout_ms,
                        )
                        return page.url
            except Exception:
                continue
        
        return None
    
    async def _try_load_more(
        self,
        page: Page,
        *,
        wait_for_selector: str | None = None,
        wait_timeout_ms: int | None = None,
    ) -> Optional[str]:
        """Try to find and click load more button.
        
        Args:
            page: Playwright page instance
            
        Returns:
            Current URL after loading more, or None
        """
        for selector in self.LOAD_MORE_SELECTORS:
            try:
                element = page.locator(selector).first
                if await element.count() > 0:
                    await element.click()
                    await self._settle_after_interaction(
                        page,
                        wait_for_selector=wait_for_selector,
                        wait_timeout_ms=wait_timeout_ms,
                    )
                    return page.url
            except Exception:
                continue
        
        return None
    
    async def _try_infinite_scroll(self, page: Page) -> Optional[str]:
        """Try infinite scroll pagination.
        
        Args:
            page: Playwright page instance
            
        Returns:
            Current URL after scrolling, or None if no more content
        """
        try:
            # Get current scroll height
            initial_height = await page.evaluate("document.body.scrollHeight")
            
            # Scroll to bottom
            await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            
            # Wait for new content
            await page.wait_for_timeout(2000)
            
            # Check if new content loaded
            new_height = await page.evaluate("document.body.scrollHeight")
            
            if new_height > initial_height:
                return page.url
            
        except Exception as e:
            logger.warning(f"Infinite scroll failed: {str(e)}")
        
        return None

    async def _settle_after_interaction(
        self,
        page: Page,
        *,
        wait_for_selector: str | None = None,
        wait_timeout_ms: int | None = None,
    ) -> None:
        try:
            await page.wait_for_load_state("networkidle", timeout=10000)
        except PlaywrightTimeoutError:
            logger.warning("Timed out waiting for network idle; using fallback delay.")
            await page.wait_for_timeout(1200)
        if wait_for_selector:
            wait_kwargs: dict[str, int] = {}
            if wait_timeout_ms and wait_timeout_ms > 0:
                wait_kwargs["timeout"] = wait_timeout_ms
            await page.wait_for_selector(wait_for_selector, **wait_kwargs)

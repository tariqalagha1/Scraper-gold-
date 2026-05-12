"""Pagination and navigation handler."""
from typing import Any
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
        '.ngx-pagination .pagination-next a',
        '.ngx-pagination .pagination-next button',
        '.ngx-pagination li.pagination-next:not(.disabled) a',
        '.ngx-pagination li.pagination-next:not(.disabled) button',
        '.pagination .next a',
        '.pagination .next button',
        'li.pagination-next a',
        'li.pagination-next button',
        '.mat-paginator-navigation-next',
        '.mat-mdc-paginator-navigation-next',
        '[rel="next"]',
        'a:has-text("Next")',
        'button:has-text("Next")',
        'a:has-text("التالي")',
        'button:has-text("التالي")',
        'a[aria-label*="Next page"]',
        'button[aria-label*="Next page"]',
        'a[aria-label*="next" i]',
        'button[aria-label*="next" i]',
        'a[title*="next" i]',
        'button[title*="next" i]',
        'a.next',
        'button.next',
        '.pagination a.next',
        'a[aria-label="Next"]',
        'a[aria-label*="Next"]',
        'button[aria-label="Next"]',
        'button[aria-label*="Next"]',
    ]

    NUMBER_PAGINATION_SELECTORS = [
        ".ngx-pagination li.current + li a",
        ".pagination li.active + li a",
        ".pagination .current + li a",
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

            url = await self._try_numbered_pagination(
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
            url = await self._try_next_button(
                page,
                wait_for_selector=wait_for_selector,
                wait_timeout_ms=wait_timeout_ms,
            )
            if url:
                return url
            return await self._try_numbered_pagination(
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
        previous_url = page.url
        previous_signature = await self._content_signature(page)
        previous_pagination_marker = await self._pagination_marker(page)

        for selector in self.NEXT_BUTTON_SELECTORS:
            try:
                for element in await self._interactable_candidates(page, selector):
                    if await self._is_disabled(element):
                        continue

                    href = await element.get_attribute("href")
                    if href and href.strip() and href.strip() not in {"#", "javascript:void(0)", "javascript:void(0);"}:
                        return urljoin(page.url, href)

                    await self._click_element(element)
                    await self._settle_after_interaction(
                        page,
                        wait_for_selector=wait_for_selector,
                        wait_timeout_ms=wait_timeout_ms,
                    )
                    if await self._did_page_progress(
                        page,
                        previous_url=previous_url,
                        previous_signature=previous_signature,
                        previous_pagination_marker=previous_pagination_marker,
                    ):
                        return page.url
            except Exception:
                continue
        
        return None

    async def _try_numbered_pagination(
        self,
        page: Page,
        *,
        wait_for_selector: str | None = None,
        wait_timeout_ms: int | None = None,
    ) -> Optional[str]:
        previous_url = page.url
        previous_signature = await self._content_signature(page)
        previous_pagination_marker = await self._pagination_marker(page)

        for selector in self.NUMBER_PAGINATION_SELECTORS:
            try:
                for element in await self._interactable_candidates(page, selector):
                    if await self._is_disabled(element):
                        continue
                    href = await element.get_attribute("href")
                    if href and href.strip() and href.strip() not in {"#", "javascript:void(0)", "javascript:void(0);"}:
                        return urljoin(page.url, href)

                    await self._click_element(element)
                    await self._settle_after_interaction(
                        page,
                        wait_for_selector=wait_for_selector,
                        wait_timeout_ms=wait_timeout_ms,
                    )
                    if await self._did_page_progress(
                        page,
                        previous_url=previous_url,
                        previous_signature=previous_signature,
                        previous_pagination_marker=previous_pagination_marker,
                    ):
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
        previous_url = page.url
        previous_signature = await self._content_signature(page)
        previous_pagination_marker = await self._pagination_marker(page)
        for selector in self.LOAD_MORE_SELECTORS:
            try:
                for element in await self._interactable_candidates(page, selector):
                    await self._click_element(element)
                    await self._settle_after_interaction(
                        page,
                        wait_for_selector=wait_for_selector,
                        wait_timeout_ms=wait_timeout_ms,
                    )
                    if await self._did_page_progress(
                        page,
                        previous_url=previous_url,
                        previous_signature=previous_signature,
                        previous_pagination_marker=previous_pagination_marker,
                    ):
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

    async def _click_element(self, element: Any) -> None:
        try:
            await element.scroll_into_view_if_needed()
        except Exception:
            pass

        try:
            await element.click(timeout=3000)
            return
        except Exception:
            await element.click(force=True, timeout=3000)

    async def _interactable_candidates(self, page: Page, selector: str, max_candidates: int = 8) -> list[Any]:
        candidates: list[Any] = []
        try:
            locator = page.locator(selector)
        except Exception:
            return candidates

        # Compatibility path for lightweight test doubles that only expose `.first`.
        if not hasattr(locator, "count") or not callable(getattr(locator, "count", None)):
            first = getattr(locator, "first", None)
            return [first] if first is not None else []

        try:
            count = min(await locator.count(), max_candidates)
        except Exception:
            first = getattr(locator, "first", None)
            return [first] if first is not None else []

        for idx in range(count):
            element = locator.nth(idx)
            try:
                is_visible = getattr(element, "is_visible", None)
                if callable(is_visible):
                    if await is_visible():
                        candidates.append(element)
                else:
                    candidates.append(element)
            except Exception:
                continue

        if candidates:
            return candidates

        # Fallback: if visibility checks are inconclusive, still try the first match.
        first = getattr(locator, "first", None)
        if first is not None and count > 0:
            candidates.append(first)
        return candidates

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

    async def _is_disabled(self, element: Any) -> bool:
        classes = str(await element.get_attribute("class") or "").lower()
        aria_disabled = str(await element.get_attribute("aria-disabled") or "").lower()
        disabled_attr = str(await element.get_attribute("disabled") or "").lower()
        if "disabled" in classes:
            return True
        if aria_disabled in {"true", "1"}:
            return True
        return disabled_attr not in {"", "false", "none", "null"}

    async def _content_signature(self, page: Page) -> str:
        try:
            signature = await page.evaluate(
                """
                () => {
                  const target = document.querySelector('table tbody')
                    || document.querySelector('[role="rowgroup"]')
                    || document.body;
                  return target && target.innerText ? target.innerText.slice(0, 4000) : '';
                }
                """
            )
            return str(signature or "")
        except Exception:
            return ""

    async def _did_page_progress(
        self,
        page: Page,
        *,
        previous_url: str,
        previous_signature: str,
        previous_pagination_marker: str,
    ) -> bool:
        if page.url != previous_url:
            return True

        for _ in range(30):
            await page.wait_for_timeout(250)
            if page.url != previous_url:
                return True
            current_pagination_marker = await self._pagination_marker(page)
            if current_pagination_marker and current_pagination_marker != previous_pagination_marker:
                return True
            current_signature = await self._content_signature(page)
            if current_signature and current_signature != previous_signature:
                return True

        return False

    async def _pagination_marker(self, page: Page) -> str:
        try:
            marker = await page.evaluate(
                """
                () => {
                  const active = document.querySelector(
                    '.ngx-pagination .current, .pagination .active, [aria-current="page"]'
                  );
                  return active && active.textContent ? active.textContent.trim() : '';
                }
                """
            )
            return str(marker or "")
        except Exception:
            return ""

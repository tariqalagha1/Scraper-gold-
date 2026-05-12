from __future__ import annotations

import asyncio
import hashlib
import random
from datetime import datetime, timezone
from typing import Any
from urllib.parse import urljoin, urlparse
from uuid import uuid4

from bs4 import BeautifulSoup
from httpx import HTTPError
from pydantic import ValidationError as PydanticValidationError
from playwright.async_api import Error as PlaywrightError
from playwright.async_api import Page, TimeoutError as PlaywrightTimeoutError

from app.agents.base_agent import BaseAgent
from app.config import settings
from app.core.exceptions import LoginError, RobotsBlockedError, ScrapingError
from app.core.logging import get_logger
from app.core.security_guard import (
    is_host_allowed_for_outbound_requests,
    normalize_and_validate_prompt,
    validate_scrape_url,
)
from app.core.retry import RetryConfig, retry_with_config
from app.schemas.scraper import (
    BrainItScrapeTaskRequest,
    ScraperAgentInsights,
    ScraperAgentMetadata,
    ScraperAgentNormalizedResult,
    ScraperAgentOutputPayload,
    ScraperAgentSummary,
    ScraperExecutionStep,
    ScraperQualityMetadata,
    ScraperSourceItem,
)
from app.scraper.browser import BrowserManager
from app.scraper.login_handler import LoginHandler
from app.scraper.page_navigator import PageNavigator
from app.scraper.rate_limiter import RateLimiter
from app.scraper.robots_checker import RobotsChecker
from app.scraper.extraction_patterns import normalize_href
from app.services.scraper_client import ScraperClient, ScraperClientError
from app.services.system_secrets import get_effective_system_secret
from app.storage.manager import StorageManager
from app.db.session import async_session_factory


logger = get_logger("app.agents.scraper_agent")
MAX_SCRAPE_ATTEMPT_TIMEOUT_MS = 45_000
MIN_SCRAPE_ATTEMPT_TIMEOUT_MS = 5_000
MAX_SELECTOR_WAIT_TIMEOUT_MS = 20_000
MIN_SELECTOR_WAIT_TIMEOUT_MS = 1_000
STEALTH_USER_AGENTS = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 15_0) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36",
)
STEALTH_ACCEPT_LANGUAGES = ("en-US,en;q=0.9", "en-GB,en;q=0.9", "en-US,en;q=0.8,ar;q=0.2")
ALLOWED_PAGINATION_TYPES = {"auto", "next", "load_more", "scroll"}
ALLOWED_PAGE_EXPANSION_MODES = {"main_only", "same_domain", "connected_external"}
MAX_LINKED_PAGE_WORKERS = 16


class ScraperAgent(BaseAgent):
    def __init__(self) -> None:
        super().__init__(agent_name="scraper_agent")
        self.scraper_client = ScraperClient.from_settings()
        self.browser_manager = BrowserManager()
        self.login_handler = LoginHandler()
        self.page_navigator = PageNavigator()
        self.robots_checker = RobotsChecker()
        self.rate_limiter = RateLimiter()
        self.storage_manager = StorageManager()

    async def execute(self, input_data: dict[str, Any]) -> dict[str, Any]:
        if self._is_remote_scrape_task(input_data):
            return await self._execute_remote_scrape_task(input_data)

        validation_error = self.validate_required_fields(input_data, ["url"])
        if validation_error:
            return self._failure_payload(url=input_data.get("url", ""), error=validation_error)

        url = input_data["url"]
        config = input_data.get("config") or {}
        credentials = input_data.get("credentials") or {}
        strategy = input_data.get("strategy") or {}
        run_id = str(input_data.get("run_id") or uuid4())
        try:
            try:
                target_error = validate_scrape_url(url, field_name="url")
                if target_error:
                    return self._failure_payload(url=url, error=target_error)
                login_url = credentials.get("login_url")
                if login_url:
                    login_error = validate_scrape_url(login_url, field_name="login_url")
                    if login_error:
                        return self._failure_payload(url=url, error=login_error)
                if isinstance(config.get("prompt"), str):
                    config["prompt"] = normalize_and_validate_prompt(config.get("prompt"))
                self.rate_limiter.set_delay(float(config.get("rate_limit_delay", config.get("delay", 1.0))))

                if config.get("respect_robots_txt", True):
                    allowed = await self.robots_checker.is_allowed(url)
                    if not allowed:
                        raise RobotsBlockedError("Target URL is blocked by robots.txt.", details={"url": url})

                page_payload = await self._scrape_with_retry(
                    url=url,
                    run_id=run_id,
                    credentials=credentials,
                    config=config,
                    strategy=strategy,
                )
                return self._success_payload(page_payload)
            except (RobotsBlockedError, LoginError, ScrapingError, PlaywrightError, HTTPError) as exc:
                self.logger.error(
                    "Scraper agent failed.",
                    agent=self.agent_name,
                    url=url,
                    error=str(exc),
                )
                return self._failure_payload(url=url, error=str(exc))
            except Exception as exc:
                self.logger.error(
                    "Unexpected scraper agent failure.",
                    agent=self.agent_name,
                    url=url,
                    error=str(exc),
                    exc_info=True,
                )
                return self._failure_payload(url=url, error=f"Unexpected scraping error: {exc}")
        finally:
            try:
                await self.browser_manager.close()
            except Exception as close_exc:
                self.logger.warning(
                    "Browser cleanup failed after scraper execution.",
                    agent=self.agent_name,
                    url=url,
                    error=str(close_exc),
                )

    @retry_with_config(
        RetryConfig(
            max_retries=2,
            delay=1.0,
            backoff_factor=2.0,
            exceptions=(PlaywrightTimeoutError, PlaywrightError, HTTPError, ScrapingError),
            jitter=False,
        )
    )
    async def _scrape_with_retry(
        self,
        *,
        url: str,
        run_id: str,
        credentials: dict[str, Any],
        config: dict[str, Any],
        strategy: dict[str, Any],
    ) -> dict[str, Any]:
        await self.rate_limiter.wait()
        runtime_config = self._build_runtime_config(config=config, strategy=strategy)
        stealth_mode = self._is_stealth_mode_enabled(config=runtime_config, strategy=strategy)
        undetected_mode = self._is_undetected_mode_enabled(config=runtime_config, strategy=strategy)
        user_agent = self._resolve_user_agent(runtime_config.get("user_agent"), stealth_mode=stealth_mode)
        extra_http_headers = (
            self._build_stealth_headers(url)
            if stealth_mode and bool(runtime_config.get("stealth_randomize_headers", True))
            else None
        )

        async with self.browser_manager.create_page(
            viewport_width=int(runtime_config.get("viewport_width", 1440)),
            viewport_height=int(runtime_config.get("viewport_height", 900)),
            user_agent=user_agent,
            extra_http_headers=extra_http_headers,
            timeout_ms=int(runtime_config.get("timeout_ms", 0)) or None,
        ) as page:
            if undetected_mode:
                await self._apply_undetected_behavior(page)
            await self._prepare_page(page)

            if credentials.get("username") and credentials.get("password"):
                login_ok = await self.login_handler.login(
                    page=page,
                    login_url=credentials.get("login_url"),
                    username=credentials["username"],
                    password=credentials["password"],
                    username_selectors=credentials.get("username_selectors"),
                    password_selectors=credentials.get("password_selectors"),
                    submit_selectors=credentials.get("submit_selectors"),
                    success_selectors=credentials.get("success_selectors"),
                    wait_until=runtime_config.get("wait_until", "networkidle"),
                )
                if not login_ok:
                    raise LoginError("Failed to authenticate with the provided credentials.")

            await self._navigate_to(page, url, runtime_config)

            max_pages = max(1, int(runtime_config.get("max_pages", 1) or 1))
            follow_pagination = self._should_follow_pagination(
                config=runtime_config,
                strategy=strategy,
            )
            follow_detail_pages = self._should_follow_detail_pages(
                config=runtime_config,
                strategy=strategy,
            )
            pagination_type = self._resolve_pagination_type(runtime_config.get("pagination_type"))
            detail_page_limit = self._resolve_detail_page_limit(
                config=runtime_config,
                strategy=strategy,
                max_pages=max_pages,
            )
            detail_stop_rule = self._resolve_detail_stop_rule(
                config=runtime_config,
                strategy=strategy,
            )

            pages: list[dict[str, Any]] = []
            seen_snapshots: set[tuple[str, str]] = set()
            seen_urls: set[str] = set()
            detail_urls_seen: set[str] = set()
            detail_urls: list[str] = []

            while len(pages) < max_pages:
                page_payload = await self._capture_page_snapshot(
                    page=page,
                    source_url=url,
                    run_id=run_id,
                    page_index=len(pages) + 1,
                )
                snapshot_signature = (page_payload["final_url"], page_payload["content_hash"])
                if snapshot_signature in seen_snapshots:
                    logger.info(
                        "Stopping pagination because page content repeated.",
                        final_url=page_payload["final_url"],
                        page_index=len(pages) + 1,
                    )
                    break

                seen_snapshots.add(snapshot_signature)
                seen_urls.add(page_payload["final_url"])
                pages.append(page_payload)

                if follow_detail_pages and len(detail_urls) < detail_page_limit:
                    discovered_detail_urls = await self._collect_detail_urls(
                        page=page,
                        strategy=strategy,
                        config=runtime_config,
                        seen_urls=seen_urls | detail_urls_seen,
                        limit=max(0, detail_page_limit - len(detail_urls)),
                    )
                    for detail_url in discovered_detail_urls:
                        if detail_url in detail_urls_seen:
                            continue
                        detail_urls.append(detail_url)
                        detail_urls_seen.add(detail_url)
                        if len(detail_urls) >= detail_page_limit:
                            break

                if len(pages) >= max_pages:
                    break

                if not follow_pagination:
                    break

                next_page_url = await self.page_navigator.get_next_page(
                    page,
                    pagination_type=pagination_type,
                    wait_for_selector=runtime_config.get("wait_for_selector"),
                    wait_timeout_ms=int(runtime_config.get("wait_for_selector_timeout_ms", runtime_config.get("timeout_ms", 0)) or 0),
                )
                if not next_page_url:
                    break

                if next_page_url != page.url and next_page_url in seen_urls:
                    logger.info(
                        "Stopping pagination because next page URL was already visited.",
                        next_page_url=next_page_url,
                    )
                    break

                if next_page_url != page.url:
                    await self._navigate_to(page, next_page_url, runtime_config)
                else:
                    await self._wait_for_optional_selector(page, runtime_config)

            remaining_page_budget = max(0, max_pages - len(pages))
            if follow_detail_pages and detail_urls and remaining_page_budget > 0:
                detail_navigation_config = self._build_detail_navigation_config(
                    config=runtime_config,
                    strategy=strategy,
                )
                selected_detail_urls = detail_urls[: min(remaining_page_budget, detail_page_limit)]
                detail_worker_count = self._resolve_linked_page_worker_count(
                    config=runtime_config,
                    strategy=strategy,
                    detail_url_count=len(selected_detail_urls),
                )
                detail_start_page_index = len(pages) + 1
                if detail_worker_count > 1:
                    detail_pages = await self._capture_detail_pages_parallel(
                        root_page=page,
                        source_url=url,
                        run_id=run_id,
                        detail_urls=selected_detail_urls,
                        detail_navigation_config=detail_navigation_config,
                        start_page_index=detail_start_page_index,
                        worker_count=detail_worker_count,
                        undetected_mode=undetected_mode,
                    )
                else:
                    detail_pages = await self._capture_detail_pages_sequential(
                        page=page,
                        source_url=url,
                        run_id=run_id,
                        detail_urls=selected_detail_urls,
                        detail_navigation_config=detail_navigation_config,
                        start_page_index=detail_start_page_index,
                    )

                if detail_stop_rule == "duplicate_title":
                    detail_pages = self._apply_duplicate_title_stop_rule(detail_pages)

                for detail_page in detail_pages:
                    if len(pages) >= max_pages:
                        break
                    detail_signature = (detail_page["final_url"], detail_page["content_hash"])
                    if detail_signature in seen_snapshots:
                        continue
                    seen_snapshots.add(detail_signature)
                    seen_urls.add(detail_page["final_url"])
                    pages.append(detail_page)

            if not pages:
                raise ScrapingError(
                    "No page snapshots were captured during scraping.",
                    details={
                        "url": url,
                        "run_id": run_id,
                        "max_pages": max_pages,
                    },
                )
            primary_page = pages[0]

            return {
                "url": url,
                "final_url": primary_page["final_url"],
                "title": primary_page["title"],
                "html_path": primary_page["html_path"],
                "screenshot_path": primary_page["screenshot_path"],
                "pages": [
                    {
                        "url": item["url"],
                        "final_url": item["final_url"],
                        "title": item["title"],
                        "html_path": item["html_path"],
                        "screenshot_path": item["screenshot_path"],
                    }
                    for item in pages
                ],
                "page_count": len(pages),
                "last_page_url": pages[-1]["final_url"],
            }

    async def _navigate_to(self, page: Page, target_url: str, config: dict[str, Any]) -> None:
        url_error = validate_scrape_url(target_url, field_name="target_url")
        if url_error:
            raise ScrapingError(
                "Blocked navigation target by security policy.",
                details={"url": target_url, "reason": url_error},
            )
        timeout_ms = int(config.get("timeout_ms", settings.PLAYWRIGHT_TIMEOUT) or settings.PLAYWRIGHT_TIMEOUT)
        attempt_timeout_seconds = max(timeout_ms / 1000.0, 1.0)

        async def _navigate_sequence() -> None:
            await page.goto(target_url, wait_until=config.get("wait_until", "networkidle"))
            await page.wait_for_load_state(config.get("post_navigation_wait_until", "networkidle"))
            await self._wait_for_optional_selector(page, config)

        try:
            await asyncio.wait_for(_navigate_sequence(), timeout=attempt_timeout_seconds)
        except asyncio.TimeoutError as exc:
            raise ScrapingError(
                "Page navigation timed out.",
                details={"url": target_url, "timeout_ms": timeout_ms},
            ) from exc
        except PlaywrightTimeoutError as exc:
            raise ScrapingError(
                "Page navigation timed out.",
                details={"url": target_url, "timeout_ms": timeout_ms},
            ) from exc
        except PlaywrightError as exc:
            raise ScrapingError(
                "Page navigation failed.",
                details={"url": target_url, "reason": str(exc)},
            ) from exc

    async def _wait_for_optional_selector(self, page: Page, config: dict[str, Any]) -> None:
        if not config.get("wait_for_selector"):
            return
        selector_timeout = int(
            config.get("wait_for_selector_timeout_ms", config.get("timeout_ms", 0)) or 0
        )
        wait_kwargs: dict[str, Any] = {}
        if selector_timeout > 0:
            wait_kwargs["timeout"] = selector_timeout
        try:
            await page.wait_for_selector(config["wait_for_selector"], **wait_kwargs)
        except PlaywrightTimeoutError:
            logger.warning(
                "Optional selector wait timed out; continuing without selector readiness.",
                selector=str(config.get("wait_for_selector")),
                timeout_ms=selector_timeout if selector_timeout > 0 else None,
                url=page.url,
            )

    def _build_runtime_config(
        self,
        *,
        config: dict[str, Any],
        strategy: dict[str, Any],
    ) -> dict[str, Any]:
        runtime_config = dict(config or {})
        selectors = strategy.get("selectors") if isinstance(strategy.get("selectors"), dict) else {}
        container_selector = str(selectors.get("container") or "").strip()
        if container_selector and not runtime_config.get("wait_for_selector"):
            runtime_config["wait_for_selector"] = container_selector

        navigation_timeout_ms = self._normalize_navigation_timeout_ms(runtime_config.get("timeout_ms"))
        runtime_config["timeout_ms"] = navigation_timeout_ms
        runtime_config["wait_for_selector_timeout_ms"] = self._normalize_selector_timeout_ms(
            runtime_config.get("wait_for_selector_timeout_ms"),
            navigation_timeout_ms=navigation_timeout_ms,
        )
        runtime_config["pagination_type"] = self._resolve_pagination_type(
            runtime_config.get("pagination_type", strategy.get("pagination_type")),
        )
        runtime_config["page_expansion_mode"] = self._resolve_page_expansion_mode(
            runtime_config.get("page_expansion_mode")
        )
        if runtime_config.get("linked_page_limit") is None:
            runtime_config["linked_page_limit"] = runtime_config.get("detail_page_limit")
        if runtime_config.get("linked_page_workers") is None:
            runtime_config["linked_page_workers"] = strategy.get("linked_page_workers")

        return runtime_config

    def _resolve_pagination_type(self, value: Any) -> str:
        normalized = str(value or "").strip().lower()
        if normalized in {"load-more", "loadmore"}:
            normalized = "load_more"
        elif normalized in {"infinite", "infinite_scroll"}:
            normalized = "scroll"

        if normalized in ALLOWED_PAGINATION_TYPES:
            return normalized
        if normalized:
            logger.warning("Ignoring unsupported pagination_type value.", pagination_type=normalized)
        return "auto"

    def _is_stealth_mode_enabled(self, *, config: dict[str, Any], strategy: dict[str, Any]) -> bool:
        return bool(config.get("stealth_mode", strategy.get("stealth_mode", False)))

    def _is_undetected_mode_enabled(self, *, config: dict[str, Any], strategy: dict[str, Any]) -> bool:
        if not self._is_stealth_mode_enabled(config=config, strategy=strategy):
            return False
        configured = config.get("stealth_undetected")
        if configured is None:
            return True
        return bool(configured)

    def _resolve_user_agent(self, configured_user_agent: Any, *, stealth_mode: bool) -> str | None:
        explicit = str(configured_user_agent or "").strip()
        if explicit:
            return explicit
        if not stealth_mode:
            return None
        return random.choice(STEALTH_USER_AGENTS)

    def _build_stealth_headers(self, target_url: str) -> dict[str, str]:
        parsed = urlparse(target_url)
        origin = f"{parsed.scheme}://{parsed.netloc}" if parsed.scheme and parsed.netloc else ""
        return {
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "Accept-Language": random.choice(STEALTH_ACCEPT_LANGUAGES),
            "Cache-Control": "max-age=0",
            "Pragma": "no-cache",
            "Upgrade-Insecure-Requests": "1",
            "DNT": "1",
            **({"Referer": origin} if origin else {}),
        }

    async def _apply_undetected_behavior(self, page: Page) -> None:
        await page.add_init_script(
            """
            Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
            Object.defineProperty(navigator, 'languages', { get: () => ['en-US', 'en'] });
            Object.defineProperty(navigator, 'platform', { get: () => 'Win32' });
            Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3, 4] });
            window.chrome = window.chrome || { runtime: {} };
            const originalQuery = window.navigator.permissions.query;
            window.navigator.permissions.query = (parameters) => (
              parameters && parameters.name === 'notifications'
                ? Promise.resolve({ state: Notification.permission })
                : originalQuery(parameters)
            );
            """
        )
        logger.info("Stealth undetected behavior enabled for scraper session.")

    def _normalize_navigation_timeout_ms(self, value: Any) -> int:
        default_timeout_ms = int(getattr(settings, "PLAYWRIGHT_TIMEOUT", 30_000) or 30_000)
        try:
            timeout_ms = int(value)
        except (TypeError, ValueError):
            timeout_ms = default_timeout_ms

        if timeout_ms <= 0:
            timeout_ms = default_timeout_ms

        return max(
            MIN_SCRAPE_ATTEMPT_TIMEOUT_MS,
            min(timeout_ms, MAX_SCRAPE_ATTEMPT_TIMEOUT_MS),
        )

    def _normalize_selector_timeout_ms(
        self,
        value: Any,
        *,
        navigation_timeout_ms: int,
    ) -> int:
        default_selector_timeout_ms = min(
            max(MIN_SELECTOR_WAIT_TIMEOUT_MS, navigation_timeout_ms // 2),
            MAX_SELECTOR_WAIT_TIMEOUT_MS,
        )
        try:
            selector_timeout_ms = int(value)
        except (TypeError, ValueError):
            selector_timeout_ms = default_selector_timeout_ms

        if selector_timeout_ms <= 0:
            selector_timeout_ms = default_selector_timeout_ms

        return max(
            MIN_SELECTOR_WAIT_TIMEOUT_MS,
            min(selector_timeout_ms, navigation_timeout_ms, MAX_SELECTOR_WAIT_TIMEOUT_MS),
        )

    def _resolve_traversal_mode(
        self,
        *,
        config: dict[str, Any],
        strategy: dict[str, Any],
    ) -> str:
        explicit_mode = str(
            config.get("traversal_mode")
            or strategy.get("traversal_mode")
            or ""
        ).strip().lower()
        if explicit_mode in {"list_harvest", "detail_drill", "single_detail"}:
            return explicit_mode

        page_type = str(strategy.get("page_type") or "").strip().lower()
        follow_pagination_requested = bool(config.get("follow_pagination", config.get("follow_links", False)))
        try:
            requested_max_pages = int(config.get("max_pages", 1) or 1)
        except (TypeError, ValueError):
            requested_max_pages = 1
        if page_type == "detail":
            if follow_pagination_requested and requested_max_pages > 1:
                logger.info(
                    "Detail classification overridden to list_harvest due explicit pagination request.",
                    requested_max_pages=requested_max_pages,
                    follow_pagination=follow_pagination_requested,
                )
                return "list_harvest"
            return "single_detail"

        prompt = str(config.get("prompt") or strategy.get("extraction_goal") or "").strip().lower()
        record_fields = {
            field.strip().lower()
            for field in strategy.get("record_fields", [])
            if str(field).strip()
        }

        detail_markers = {"description", "summary", "availability", "sku", "details", "specifications", "rating"}
        detail_prompt_markers = {
            "each product page",
            "detail page",
            "detail pages",
            "open product pages",
            "visit each item",
            "visit each product",
            "from each product",
            "from each item",
        }

        if page_type == "list" and (
            record_fields & detail_markers
            or any(marker in prompt for marker in detail_prompt_markers)
        ):
            return "detail_drill"

        return "list_harvest"

    def _resolve_detail_page_limit(
        self,
        *,
        config: dict[str, Any],
        strategy: dict[str, Any],
        max_pages: int,
    ) -> int:
        explicit_value = config.get("detail_page_limit", strategy.get("detail_page_limit"))
        if explicit_value is None:
            explicit_value = config.get("linked_page_limit")
        try:
            explicit_limit = int(explicit_value)
        except (TypeError, ValueError):
            explicit_limit = max(1, max_pages - 1)
        return max(1, min(explicit_limit, max(1, max_pages - 1)))

    def _resolve_linked_page_worker_count(
        self,
        *,
        config: dict[str, Any],
        strategy: dict[str, Any],
        detail_url_count: int,
    ) -> int:
        if detail_url_count <= 1:
            return 1

        explicit_value = config.get("linked_page_workers", strategy.get("linked_page_workers"))
        try:
            requested_workers = int(explicit_value)
        except (TypeError, ValueError):
            requested_workers = min(4, detail_url_count)

        bounded_workers = max(1, min(requested_workers, MAX_LINKED_PAGE_WORKERS, detail_url_count))
        return bounded_workers

    def _resolve_page_expansion_mode(self, value: Any) -> str:
        normalized = str(value or "").strip().lower()
        return normalized if normalized in ALLOWED_PAGE_EXPANSION_MODES else "same_domain"

    def _resolve_detail_stop_rule(
        self,
        *,
        config: dict[str, Any],
        strategy: dict[str, Any],
    ) -> str:
        explicit_rule = str(
            config.get("detail_stop_rule")
            or strategy.get("detail_stop_rule")
            or ""
        ).strip().lower()
        if explicit_rule in {"budget_only", "duplicate_title"}:
            return explicit_rule
        return "budget_only"

    def _should_stop_after_detail_capture(
        self,
        *,
        page_payload: dict[str, Any],
        detail_stop_rule: str,
        detail_titles_seen: set[str],
    ) -> tuple[bool, bool]:
        if detail_stop_rule != "duplicate_title":
            return False, False

        title_signature = str(page_payload.get("title") or "").strip().lower()
        if not title_signature:
            return False, False

        if title_signature in detail_titles_seen:
            return True, True
        return False, False

    def _should_follow_pagination(
        self,
        *,
        config: dict[str, Any],
        strategy: dict[str, Any],
    ) -> bool:
        traversal_mode = self._resolve_traversal_mode(config=config, strategy=strategy)
        requested = bool(config.get("follow_pagination", config.get("follow_links", True)))
        if not requested:
            return False

        if traversal_mode in {"detail_drill", "single_detail"}:
            return False

        prompt = str(config.get("prompt") or strategy.get("extraction_goal") or "").strip().lower()
        if not prompt:
            return requested

        single_page_markers = {
            "this page",
            "single page",
            "detail page",
            "specific item",
            "specific product",
        }
        if any(marker in prompt for marker in single_page_markers):
            return False

        return requested

    def _should_follow_detail_pages(
        self,
        *,
        config: dict[str, Any],
        strategy: dict[str, Any],
    ) -> bool:
        page_type = str(strategy.get("page_type") or "").strip().lower()
        explicit = config.get("follow_detail_pages")
        if explicit is not None:
            return bool(explicit)

        page_expansion_mode = self._resolve_page_expansion_mode(config.get("page_expansion_mode"))
        if page_expansion_mode == "main_only":
            return False
        if page_expansion_mode in {"same_domain", "connected_external"} and page_type != "detail":
            return True

        traversal_mode = self._resolve_traversal_mode(config=config, strategy=strategy)
        if traversal_mode == "detail_drill":
            return page_type == "list"
        if traversal_mode in {"list_harvest", "single_detail"}:
            return False

        if page_type != "list":
            return False

        record_fields = {
            field.strip().lower()
            for field in strategy.get("record_fields", [])
            if str(field).strip()
        }
        detail_markers = {"description", "summary", "availability", "sku", "details", "specifications", "rating"}
        if record_fields & detail_markers:
            return True

        prompt = str(config.get("prompt") or strategy.get("extraction_goal") or "").strip().lower()
        if not prompt:
            return False

        prompt_markers = {
            "each product page",
            "detail page",
            "open product pages",
            "visit each item",
            "from each product",
            "from each item",
        }
        return any(marker in prompt for marker in prompt_markers)

    def _build_detail_navigation_config(
        self,
        *,
        config: dict[str, Any],
        strategy: dict[str, Any],
    ) -> dict[str, Any]:
        detail_config = dict(config or {})
        wait_for_selector = str(detail_config.get("wait_for_selector") or "").strip()
        if not wait_for_selector:
            return detail_config

        selectors = strategy.get("selectors") if isinstance(strategy.get("selectors"), dict) else {}
        container_selector = str(selectors.get("container") or "").strip()
        detail_link_selector = str(detail_config.get("detail_link_selector") or "").strip()

        if wait_for_selector in {container_selector, detail_link_selector}:
            detail_config.pop("wait_for_selector", None)
            detail_config.pop("wait_for_selector_timeout_ms", None)

        return detail_config

    async def _collect_detail_urls(
        self,
        *,
        page: Page,
        strategy: dict[str, Any],
        config: dict[str, Any],
        seen_urls: set[str],
        limit: int,
    ) -> list[str]:
        if limit <= 0:
            return []

        html = await page.content()
        soup = BeautifulSoup(html or "", "lxml")
        selectors = strategy.get("selectors") if isinstance(strategy.get("selectors"), dict) else {}
        field_selectors = selectors.get("fields") if isinstance(selectors.get("fields"), dict) else {}
        detail_link_selector = str(
            config.get("detail_link_selector")
            or field_selectors.get("link")
            or "article a[href], li a[href], .item a[href], .product a[href]"
        ).strip()
        expansion_mode = self._resolve_page_expansion_mode(config.get("page_expansion_mode"))
        allow_external_domains = expansion_mode == "connected_external"
        raw_keywords = config.get("linked_page_keywords")
        linked_page_keywords = {
            str(item).strip().lower()
            for item in (raw_keywords if isinstance(raw_keywords, list) else [])
            if str(item).strip()
        }

        current_domain = urlparse(page.url).netloc.lower()
        candidates: list[str] = []
        try:
            detail_nodes = soup.select(detail_link_selector)
        except Exception as exc:
            logger.warning(
                "Invalid detail link selector; falling back to generic anchors.",
                selector=detail_link_selector,
                error=str(exc),
            )
            detail_nodes = soup.select("a[href]")

        for node in detail_nodes:
            href = normalize_href(node.get("href"))
            if not href:
                continue
            absolute_url = urljoin(page.url, href)
            if not absolute_url or absolute_url in seen_urls or absolute_url in candidates:
                continue
            link_text = str(node.get_text(" ", strip=True) or "").strip().lower()
            if linked_page_keywords:
                haystack = f"{absolute_url.lower()} {link_text}"
                if not any(keyword in haystack for keyword in linked_page_keywords):
                    continue
            if validate_scrape_url(absolute_url, field_name="detail_url"):
                continue
            if not allow_external_domains and urlparse(absolute_url).netloc.lower() != current_domain:
                continue
            candidates.append(absolute_url)
            if len(candidates) >= limit:
                break

        return candidates

    async def _capture_detail_pages_sequential(
        self,
        *,
        page: Page,
        source_url: str,
        run_id: str,
        detail_urls: list[str],
        detail_navigation_config: dict[str, Any],
        start_page_index: int,
    ) -> list[dict[str, Any]]:
        captured: list[dict[str, Any]] = []
        for offset, detail_url in enumerate(detail_urls):
            try:
                await self._navigate_to(page, detail_url, detail_navigation_config)
                captured.append(
                    await self._capture_page_snapshot(
                        page=page,
                        source_url=source_url,
                        run_id=run_id,
                        page_index=start_page_index + offset,
                    )
                )
            except Exception as exc:
                logger.warning(
                    "Linked page scrape failed; continuing.",
                    detail_url=detail_url,
                    error=str(exc),
                )
        return captured

    async def _capture_detail_pages_parallel(
        self,
        *,
        root_page: Page,
        source_url: str,
        run_id: str,
        detail_urls: list[str],
        detail_navigation_config: dict[str, Any],
        start_page_index: int,
        worker_count: int,
        undetected_mode: bool,
    ) -> list[dict[str, Any]]:
        if not detail_urls:
            return []

        semaphore = asyncio.Semaphore(max(1, worker_count))
        captured_payloads: list[dict[str, Any] | None] = [None] * len(detail_urls)
        context = root_page.context

        async def _worker(index: int, detail_url: str) -> None:
            async with semaphore:
                worker_page: Page | None = None
                try:
                    worker_page = await context.new_page()
                    if undetected_mode:
                        await self._apply_undetected_behavior(worker_page)
                    await self._prepare_page(worker_page)
                    await self._navigate_to(worker_page, detail_url, detail_navigation_config)
                    captured_payloads[index] = await self._capture_page_snapshot(
                        page=worker_page,
                        source_url=source_url,
                        run_id=run_id,
                        page_index=start_page_index + index,
                    )
                except Exception as exc:
                    logger.warning(
                        "Parallel linked-page worker failed; continuing.",
                        detail_url=detail_url,
                        error=str(exc),
                    )
                finally:
                    if worker_page is not None:
                        try:
                            await worker_page.close()
                        except Exception:
                            logger.warning("Failed to close parallel linked-page worker browser tab.", detail_url=detail_url)

        await asyncio.gather(*(_worker(index, detail_url) for index, detail_url in enumerate(detail_urls)))
        return [payload for payload in captured_payloads if payload is not None]

    def _apply_duplicate_title_stop_rule(self, detail_pages: list[dict[str, Any]]) -> list[dict[str, Any]]:
        filtered: list[dict[str, Any]] = []
        seen_titles: set[str] = set()
        for detail_page in detail_pages:
            title_signature = str(detail_page.get("title") or "").strip().lower()
            if title_signature and title_signature in seen_titles:
                continue
            if title_signature:
                seen_titles.add(title_signature)
            filtered.append(detail_page)
        return filtered

    async def _capture_page_snapshot(
        self,
        *,
        page: Page,
        source_url: str,
        run_id: str,
        page_index: int,
    ) -> dict[str, Any]:
        final_url = page.url
        title = (await page.title()).strip()
        html = await page.content()
        if not title:
            title = self._extract_fallback_title(html)
        screenshot_bytes = await page.screenshot(full_page=True, type="png")
        suffix = f"page_{page_index:02d}"

        html_path = self.storage_manager.save_raw_html(
            run_id,
            final_url,
            html,
            filename_suffix=suffix,
        )
        screenshot_path = self.storage_manager.save_screenshot(
            run_id,
            final_url,
            screenshot_bytes,
            filename_suffix=suffix,
        )

        logger.info(
            "Scrape capture completed.",
            url=source_url,
            final_url=final_url,
            title=title,
            html_path=html_path,
            screenshot_path=screenshot_path,
            page_index=page_index,
        )

        return {
            "url": source_url,
            "final_url": final_url,
            "title": title,
            "html_path": html_path,
            "screenshot_path": screenshot_path,
            "content_hash": hashlib.md5(html.encode("utf-8")).hexdigest(),
        }

    def _extract_fallback_title(self, html: str) -> str:
        soup = BeautifulSoup(html or "", "lxml")
        for selector in ("h1", "main h2", "article h2", "h2", "h3", "title"):
            node = soup.select_one(selector)
            if node:
                text = node.get_text(" ", strip=True)
                if text:
                    return text
        return ""

    async def _prepare_page(self, page: Page) -> None:
        def handle_request_failed(request: Any) -> None:
            logger.warning(
                "Network request failed during scraping.",
                url=request.url,
                method=request.method,
                failure=request.failure,
            )

        page.on("requestfailed", handle_request_failed)
        await page.route("**/*", self._guard_outbound_request)

    async def _guard_outbound_request(self, route: Any) -> None:
        request = route.request
        parsed = urlparse(str(request.url or ""))
        hostname = (parsed.hostname or "").strip().lower()

        if parsed.scheme not in {"http", "https"}:
            await route.abort()
            return
        if hostname and not is_host_allowed_for_outbound_requests(hostname):
            logger.warning("Blocked outbound browser request by security guard.", url=request.url, host=hostname)
            await route.abort()
            return

        await route.continue_()

    def _is_remote_scrape_task(self, input_data: dict[str, Any]) -> bool:
        task_type = str(input_data.get("task_type") or "").strip().lower()
        return task_type == "scrape" and isinstance(input_data.get("input_payload"), dict)

    def _resolve_remote_request_id(self, request: BrainItScrapeTaskRequest, input_data: dict[str, Any]) -> str:
        explicit = str(request.input_payload.request_id or "").strip()
        if explicit:
            return explicit

        for key in ("task_id", "run_id", "job_id"):
            candidate = str(input_data.get(key) or "").strip()
            if candidate:
                return candidate
        return str(uuid4())

    def _normalize_remote_status(self, status: str, total: int, errors: list[str]) -> str:
        normalized = str(status or "").strip().lower()
        if normalized in {"completed", "partial", "failed"}:
            if normalized == "completed" and errors:
                return "partial"
            if normalized == "partial" and total <= 0:
                return "failed"
            if normalized == "failed":
                return "failed"
            return normalized
        if total <= 0:
            return "failed"
        return "partial" if errors else "completed"

    def _build_insights(
        self,
        *,
        total: int,
        sources: list[ScraperSourceItem],
        quality: ScraperQualityMetadata,
        errors: list[str],
        requested_limit: int,
    ) -> ScraperAgentInsights:
        source_count = len(sources)
        coverage = float(quality.coverage)
        confidence = float(quality.confidence)
        missing_fields = dict(quality.missing_fields or {})
        duplicates_removed = int(quality.duplicates_removed)
        errors_count = len(errors)

        coverage_label = "high" if coverage >= 0.8 else "moderate" if coverage >= 0.6 else "low"
        confidence_label = "high" if confidence >= 0.8 else "moderate" if confidence >= 0.6 else "low"
        top_missing_field = ""
        top_missing_count = 0
        if missing_fields:
            top_missing_field, top_missing_count = sorted(
                ((field, int(count)) for field, count in missing_fields.items()),
                key=lambda item: (-item[1], item[0]),
            )[0]

        summary = (
            f"Found {total} record(s) across {source_count} source(s). "
            f"Coverage is {coverage_label} ({coverage:.2f}) and confidence is {confidence_label} ({confidence:.2f})."
        )
        if top_missing_count > 0:
            summary += f" {top_missing_field} data is incomplete."

        findings: list[str] = []
        if sources:
            top_source = sorted(sources, key=lambda item: (-int(item.count), item.name))[0]
            findings.append(f"Most records came from {top_source.name} ({top_source.count}).")
        else:
            findings.append("No source distribution was reported.")

        if top_missing_count > 0:
            findings.append(f"{top_missing_field} is the most incomplete field ({top_missing_count} missing).")
        else:
            findings.append("Requested fields are complete in returned records.")

        raw_total = total + max(0, duplicates_removed)
        duplicate_impact = (duplicates_removed / raw_total) if raw_total > 0 else 0.0
        findings.append(
            f"Duplicate removal removed {duplicates_removed} record(s) ({duplicate_impact:.1%} impact)."
        )

        if errors_count > 0:
            findings.append(f"The scraper reported {errors_count} error(s).")
        else:
            findings.append("No scraper errors were reported.")

        findings.append(f"Coverage is {coverage:.2f} with confidence {confidence:.2f}.")
        findings = findings[:5]
        if len(findings) < 3:
            findings.append(f"Returned {total} record(s) out of requested limit {requested_limit}.")
        findings = findings[:5]

        if total <= 0:
            data_quality_note = "Result quality is low because no usable records were returned."
        elif confidence >= 0.8 and coverage >= 0.8 and errors_count == 0 and top_missing_count == 0:
            data_quality_note = "Result quality is high."
        elif confidence >= 0.6 and coverage >= 0.6:
            data_quality_note = "Result is usable but some requested fields are missing."
        else:
            data_quality_note = "Result quality is limited; review missing fields and reported errors."

        if total <= 0:
            recommended_next_step = "Refine the query or location and run again."
        elif errors_count > 0:
            recommended_next_step = "Retry the request to recover records from failed sources."
        elif top_missing_field == "email" and top_missing_count > 0:
            recommended_next_step = "Filter for records with email addresses."
        elif total < requested_limit:
            recommended_next_step = "Request more records to improve coverage."
        else:
            recommended_next_step = "Refine the search by city to improve precision."

        return ScraperAgentInsights(
            summary=summary,
            key_findings=findings,
            data_quality_note=data_quality_note,
            recommended_next_step=recommended_next_step,
        )

    async def _execute_remote_scrape_task(self, input_data: dict[str, Any]) -> dict[str, Any]:
        try:
            request = BrainItScrapeTaskRequest.model_validate(input_data)
        except PydanticValidationError as exc:
            return self._build_failure(
                "Invalid scrape task input payload.",
                data={"validation_errors": exc.errors()},
            )

        request_payload = request.input_payload.model_copy(
            update={"request_id": self._resolve_remote_request_id(request, input_data)}
        )
        try:
            async with async_session_factory() as db:
                effective_scraper_key = await get_effective_system_secret(db, "SCRAPER_API_KEY")
                if str(effective_scraper_key or "").strip():
                    self.scraper_client.api_key = str(effective_scraper_key).strip()
        except Exception as exc:
            logger.warning("Could not load system SCRAPER_API_KEY override.", error=str(exc))
        input_summary = {
            "query": request_payload.query,
            "location": request_payload.location,
            "limit": request_payload.limit,
            "fields_count": len(request_payload.fields),
        }
        try:
            scraper_response = await self.scraper_client.scrape(request_payload)
        except ScraperClientError as exc:
            failed_quality = ScraperQualityMetadata(
                duplicates_removed=0,
                coverage=0.0,
                confidence=0.0,
                missing_fields={},
                normalized_fields=0,
            )
            failed_result = ScraperAgentNormalizedResult(
                status="failed",
                summary=ScraperAgentSummary(total=0, coverage=0.0, confidence=0.0),
                output_payload=ScraperAgentOutputPayload(
                    data=[],
                    sources=[],
                    quality=failed_quality,
                    errors=[exc.message],
                    request_id=request_payload.request_id or "",
                    execution_time=0.0,
                ),
                insights=self._build_insights(
                    total=0,
                    sources=[],
                    quality=failed_quality,
                    errors=[exc.message],
                    requested_limit=request_payload.limit,
                ),
                execution_steps=[
                    ScraperExecutionStep(
                        step=1,
                        status="failed",
                        input_summary=input_summary,
                        output_summary={"error_code": exc.code, "http_status": exc.status_code},
                    )
                ],
                metadata=ScraperAgentMetadata(),
                scraper_confidence=0.0,
            )
            return self._build_failure(
                exc.message,
                data=failed_result.model_dump(),
            )

        response_data = list(scraper_response.data)
        total_count = len(response_data)
        normalized_status = self._normalize_remote_status(
            scraper_response.status,
            total_count,
            scraper_response.errors,
        )
        normalized_result = ScraperAgentNormalizedResult(
            status=normalized_status,  # type: ignore[arg-type]
            summary=ScraperAgentSummary(
                total=total_count,
                coverage=scraper_response.quality.coverage,
                confidence=scraper_response.quality.confidence,
            ),
            output_payload=ScraperAgentOutputPayload(
                data=response_data,
                sources=scraper_response.sources,
                quality=scraper_response.quality,
                errors=scraper_response.errors,
                request_id=scraper_response.request_id,
                execution_time=scraper_response.execution_time,
            ),
            insights=self._build_insights(
                total=total_count,
                sources=scraper_response.sources,
                quality=scraper_response.quality,
                errors=scraper_response.errors,
                requested_limit=request_payload.limit,
            ),
            execution_steps=[
                ScraperExecutionStep(
                    step=1,
                    status=normalized_status,
                    input_summary=input_summary,
                    output_summary={
                        "total": total_count,
                        "coverage": scraper_response.quality.coverage,
                        "confidence": scraper_response.quality.confidence,
                    },
                )
            ],
            metadata=ScraperAgentMetadata(),
            scraper_confidence=scraper_response.quality.confidence,
        )
        if normalized_status == "failed":
            return self._build_failure(
                "Smart Scraper returned failed status.",
                data=normalized_result.model_dump(),
            )
        return self._build_success(normalized_result.model_dump())

    def _success_payload(self, data: dict[str, Any]) -> dict[str, Any]:
        return {
            "status": "success",
            "data": {
                "url": data["url"],
                "final_url": data["final_url"],
                "title": data["title"],
                "html_path": data["html_path"],
                "screenshot_path": data["screenshot_path"],
                **({"pages": data["pages"]} if "pages" in data else {}),
            },
            "error": None,
            "metadata": {
                "agent": self.agent_name,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
        }

    def _failure_payload(self, *, url: str, error: str) -> dict[str, Any]:
        return {
            "status": "fail",
            "data": {
                "url": url,
                "final_url": "",
                "title": "",
                "html_path": "",
                "screenshot_path": "",
            },
            "error": error,
            "metadata": {
                "agent": self.agent_name,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
        }


async def example_usage() -> dict[str, Any]:
    agent = ScraperAgent()
    return await agent.safe_execute(
        {
            "url": "https://example.com",
            "run_id": "example-run",
            "config": {
                "respect_robots_txt": True,
                "rate_limit_delay": 1.0,
                "wait_until": "domcontentloaded",
            },
        }
    )

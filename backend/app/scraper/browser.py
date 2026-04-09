from contextlib import asynccontextmanager
from pathlib import Path
import platform
import tempfile
from typing import Any, AsyncIterator, Optional

from playwright.async_api import Browser, BrowserContext, Page, Playwright, async_playwright

from app.config import settings
from app.core.logging import get_logger


logger = get_logger("app.scraper.browser")
FULL_CHROMIUM_EXECUTABLE = Path(
    "/Users/tariq/Library/Caches/ms-playwright/chromium-1208/chrome-mac-x64/"
    "Google Chrome for Testing.app/Contents/MacOS/Google Chrome for Testing"
)
LOCAL_CHROME_EXECUTABLE = Path(
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
)


class BrowserManager:
    def __init__(self) -> None:
        self._playwright: Optional[Playwright] = None
        self._browser: Optional[Browser] = None

    async def _probe_browser_health(self, browser: Browser, timeout_ms: int) -> None:
        """Fail fast if the launched browser cannot render a basic page.

        This probe must stay offline-safe. Using a real URL here can stall the
        whole scraping pipeline in local or restricted environments before the
        target page is ever visited.
        """
        context: Optional[BrowserContext] = None
        try:
            context = await browser.new_context()
            page = await context.new_page()
            page.set_default_timeout(timeout_ms)
            page.set_default_navigation_timeout(timeout_ms)
            await page.set_content(
                "<html><head><title>browser-ok</title></head><body><main>ready</main></body></html>",
                wait_until="domcontentloaded",
                timeout=timeout_ms,
            )
            title = await page.title()
            if title != "browser-ok":
                raise RuntimeError("Browser health probe did not render expected content.")
        finally:
            if context is not None:
                await context.close()

    async def _ensure_browser(self) -> Browser:
        if self._browser is None:
            self._playwright = await async_playwright().start()
            launched_headless = settings.PLAYWRIGHT_HEADLESS
            launch_timeout_ms = 60000
            sandbox_home = str(Path(tempfile.gettempdir()) / "smart_scraper_pw_home")
            Path(sandbox_home).mkdir(parents=True, exist_ok=True)
            launch_env = {
                "HOME": sandbox_home,
                "XDG_CONFIG_HOME": str(Path(sandbox_home) / ".config"),
                "XDG_CACHE_HOME": str(Path(sandbox_home) / ".cache"),
                "XDG_DATA_HOME": str(Path(sandbox_home) / ".local" / "share"),
            }
            Path(launch_env["XDG_CONFIG_HOME"]).mkdir(parents=True, exist_ok=True)
            Path(launch_env["XDG_CACHE_HOME"]).mkdir(parents=True, exist_ok=True)
            Path(launch_env["XDG_DATA_HOME"]).mkdir(parents=True, exist_ok=True)
            launch_args = [
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--disable-dev-shm-usage",
                "--disable-gpu",
                "--no-first-run",
                "--no-zygote",
                "--single-process",
                "--disable-crash-reporter",
                "--disable-crashpad",
            ]
            launch_attempts: list[dict[str, Any]] = [{"channel": "chrome"}]
            if LOCAL_CHROME_EXECUTABLE.exists():
                launch_attempts.append({"executable_path": str(LOCAL_CHROME_EXECUTABLE)})
            launch_attempts.append({"executable_path": str(FULL_CHROMIUM_EXECUTABLE)})
            # Safety fallback: let Playwright pick managed Chromium when explicit paths fail.
            launch_attempts.append({})

            launch_errors: list[str] = []
            is_macos = platform.system().lower() == "darwin"

            for attempt in launch_attempts:
                launch_label = (
                    f"channel:{attempt['channel']}"
                    if attempt.get("channel")
                    else f"path:{attempt.get('executable_path')}"
                )
                logger.info(
                    "Launching Chromium.",
                    mode=launch_label,
                    headless=settings.PLAYWRIGHT_HEADLESS,
                    sandbox_home=sandbox_home,
                )
                try:
                    self._browser = await self._playwright.chromium.launch(
                        headless=settings.PLAYWRIGHT_HEADLESS,
                        channel=attempt.get("channel"),
                        executable_path=attempt.get("executable_path"),
                        timeout=launch_timeout_ms,
                        args=launch_args,
                        env=launch_env,
                    )
                    await self._probe_browser_health(self._browser, launch_timeout_ms)
                    logger.info(
                        "Playwright browser launched.",
                        mode=launch_label,
                        headless=launched_headless,
                    )
                    break
                except Exception as exc:
                    if self._browser is not None:
                        try:
                            await self._browser.close()
                        except Exception:
                            pass
                        self._browser = None
                    launch_errors.append(f"{launch_label}: {exc}")
                    logger.warning(
                        "Chromium launch attempt failed.",
                        mode=launch_label,
                        headless=settings.PLAYWRIGHT_HEADLESS,
                        error=str(exc),
                    )

            if self._browser is None and is_macos and settings.PLAYWRIGHT_HEADLESS:
                for attempt in launch_attempts:
                    launch_label = (
                        f"channel:{attempt['channel']}:headful"
                        if attempt.get("channel")
                        else f"path:{attempt.get('executable_path')}:headful"
                    )
                    logger.warning(
                        "Retrying Chromium launch in headful mode on macOS fallback.",
                        mode=launch_label,
                    )
                    try:
                        self._browser = await self._playwright.chromium.launch(
                            headless=False,
                            channel=attempt.get("channel"),
                            executable_path=attempt.get("executable_path"),
                            timeout=launch_timeout_ms,
                            args=launch_args,
                            env=launch_env,
                        )
                        await self._probe_browser_health(self._browser, launch_timeout_ms)
                        launched_headless = False
                        logger.info(
                            "Playwright browser launched via macOS headful fallback.",
                            mode=launch_label,
                            headless=False,
                        )
                        break
                    except Exception as exc:
                        if self._browser is not None:
                            try:
                                await self._browser.close()
                            except Exception:
                                pass
                            self._browser = None
                        launch_errors.append(f"{launch_label}: {exc}")
                        logger.warning(
                            "Chromium headful fallback attempt failed.",
                            mode=launch_label,
                            error=str(exc),
                        )

            if self._browser is None:
                raise RuntimeError(
                    "Failed to launch Chromium. Attempts: " + " | ".join(launch_errors)
                )
            logger.info(
                "Browser session ready.",
                headless=launched_headless,
            )
        return self._browser

    @asynccontextmanager
    async def create_context(
        self,
        *,
        viewport_width: int = 1440,
        viewport_height: int = 900,
        user_agent: Optional[str] = None,
        extra_http_headers: Optional[dict[str, str]] = None,
        timeout_ms: Optional[int] = None,
    ) -> AsyncIterator[BrowserContext]:
        browser = await self._ensure_browser()
        context_options: dict[str, Any] = {
            "viewport": {"width": viewport_width, "height": viewport_height},
            "ignore_https_errors": True,
        }
        if user_agent:
            context_options["user_agent"] = user_agent
        if extra_http_headers:
            context_options["extra_http_headers"] = extra_http_headers

        context = await browser.new_context(**context_options)
        resolved_timeout = max(int(timeout_ms or settings.PLAYWRIGHT_TIMEOUT or 30000), 1000)
        context.set_default_timeout(resolved_timeout)
        context.set_default_navigation_timeout(resolved_timeout)
        try:
            yield context
        finally:
            await context.close()

    @asynccontextmanager
    async def create_page(
        self,
        *,
        viewport_width: int = 1440,
        viewport_height: int = 900,
        user_agent: Optional[str] = None,
        extra_http_headers: Optional[dict[str, str]] = None,
        timeout_ms: Optional[int] = None,
    ) -> AsyncIterator[Page]:
        async with self.create_context(
            viewport_width=viewport_width,
            viewport_height=viewport_height,
            user_agent=user_agent,
            extra_http_headers=extra_http_headers,
            timeout_ms=timeout_ms,
        ) as context:
            page = await context.new_page()
            resolved_timeout = max(int(timeout_ms or settings.PLAYWRIGHT_TIMEOUT or 30000), 1000)
            page.set_default_timeout(resolved_timeout)
            page.set_default_navigation_timeout(resolved_timeout)
            yield page

    async def close(self) -> None:
        if self._browser is not None:
            await self._browser.close()
            self._browser = None
        if self._playwright is not None:
            await self._playwright.stop()
            self._playwright = None
        logger.info("Playwright browser closed.")

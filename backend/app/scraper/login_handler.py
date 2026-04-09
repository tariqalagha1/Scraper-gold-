from typing import Any, Optional

from playwright.async_api import Page, TimeoutError as PlaywrightTimeoutError

from app.core.logging import get_logger


logger = get_logger("app.scraper.login_handler")


class LoginHandler:
    USERNAME_SELECTORS = [
        'input[name="username"]',
        'input[name="email"]',
        'input[name="user"]',
        'input[name="login"]',
        'input[type="email"]',
        "#username",
        "#email",
        "#user",
        'input[id*="user"]',
        'input[id*="email"]',
        'input[autocomplete="username"]',
    ]
    PASSWORD_SELECTORS = [
        'input[name="password"]',
        'input[name="pass"]',
        'input[type="password"]',
        "#password",
        "#pass",
        'input[id*="password"]',
        'input[id*="pass"]',
        'input[autocomplete="current-password"]',
    ]
    SUBMIT_SELECTORS = [
        'button[type="submit"]',
        'input[type="submit"]',
        'button:has-text("Log in")',
        'button:has-text("Login")',
        'button:has-text("Sign in")',
        'button:has-text("Continue")',
        '[type="submit"]',
    ]
    SUCCESS_SELECTORS = [
        'text="Logout"',
        'text="Sign out"',
        'text="Dashboard"',
        'text="My Account"',
        '[href*="logout"]',
    ]
    ERROR_SELECTORS = [
        'text="Invalid"',
        'text="incorrect"',
        'text="failed"',
        ".error",
        ".alert-danger",
        '[role="alert"]',
    ]

    async def login(
        self,
        *,
        page: Page,
        login_url: Optional[str],
        username: str,
        password: str,
        username_selectors: Optional[list[str]] = None,
        password_selectors: Optional[list[str]] = None,
        submit_selectors: Optional[list[str]] = None,
        success_selectors: Optional[list[str]] = None,
        wait_until: str = "networkidle",
    ) -> bool:
        if login_url:
            await page.goto(login_url, wait_until=wait_until)

        username_ok = await self._fill_first(page, username_selectors or self.USERNAME_SELECTORS, username)
        password_ok = await self._fill_first(page, password_selectors or self.PASSWORD_SELECTORS, password)
        if not username_ok or not password_ok:
            logger.warning(
                "Login fields not found.",
                username_found=username_ok,
                password_found=password_ok,
            )
            return False

        await self._submit(page, submit_selectors or self.SUBMIT_SELECTORS)

        try:
            await page.wait_for_load_state(wait_until)
        except PlaywrightTimeoutError:
            logger.warning("Login load state timed out; continuing with verification.")

        success = await self._verify_login(
            page=page,
            login_url=login_url,
            success_selectors=success_selectors or self.SUCCESS_SELECTORS,
        )
        logger.info("Login flow completed.", success=success, current_url=page.url)
        return success

    async def _fill_first(self, page: Page, selectors: list[str], value: str) -> bool:
        for selector in selectors:
            try:
                locator = page.locator(selector).first
                if await locator.count() > 0:
                    await locator.fill(value)
                    return True
            except Exception:
                continue
        return False

    async def _submit(self, page: Page, selectors: list[str]) -> None:
        for selector in selectors:
            try:
                locator = page.locator(selector).first
                if await locator.count() > 0:
                    await locator.click()
                    return
            except Exception:
                continue
        await page.keyboard.press("Enter")

    async def _verify_login(
        self,
        *,
        page: Page,
        login_url: Optional[str],
        success_selectors: list[str],
    ) -> bool:
        for selector in self.ERROR_SELECTORS:
            try:
                if await page.locator(selector).count() > 0:
                    return False
            except Exception:
                continue

        if login_url and page.url != login_url:
            return True

        for selector in success_selectors:
            try:
                if await page.locator(selector).count() > 0:
                    return True
            except Exception:
                continue

        password_inputs = page.locator('input[type="password"]')
        try:
            if await password_inputs.count() > 0:
                return False
        except Exception:
            pass

        return True

import pytest

from app.scraper.browser import BrowserManager


class _FakePage:
    def __init__(self) -> None:
        self.goto_called = False
        self.content_calls = []

    def set_default_timeout(self, timeout_ms: int) -> None:
        self.timeout_ms = timeout_ms

    def set_default_navigation_timeout(self, timeout_ms: int) -> None:
        self.navigation_timeout_ms = timeout_ms

    async def goto(self, *_args, **_kwargs) -> None:
        self.goto_called = True

    async def set_content(self, html: str, **kwargs) -> None:
        self.content_calls.append((html, kwargs))

    async def title(self) -> str:
        return "browser-ok"


class _FakeContext:
    def __init__(self, page: _FakePage) -> None:
        self.page = page
        self.closed = False
        self.timeout_ms = None
        self.navigation_timeout_ms = None

    async def new_page(self) -> _FakePage:
        return self.page

    def set_default_timeout(self, timeout_ms: int) -> None:
        self.timeout_ms = timeout_ms

    def set_default_navigation_timeout(self, timeout_ms: int) -> None:
        self.navigation_timeout_ms = timeout_ms

    async def close(self) -> None:
        self.closed = True


class _FakeBrowser:
    def __init__(self, context: _FakeContext) -> None:
        self.context = context

    async def new_context(self, **_kwargs) -> _FakeContext:
        return self.context

    def is_connected(self) -> bool:
        return True


class _FlakyBrowser:
    def __init__(self, context: _FakeContext) -> None:
        self.context = context
        self.calls = 0

    async def new_context(self, **_kwargs) -> _FakeContext:
        self.calls += 1
        if self.calls == 1:
            raise RuntimeError("Target page, context or browser has been closed")
        return self.context

    def is_connected(self) -> bool:
        return True


@pytest.mark.asyncio
async def test_probe_browser_health_uses_inline_content_not_network_navigation():
    page = _FakePage()
    context = _FakeContext(page)
    browser = _FakeBrowser(context)

    manager = BrowserManager()
    await manager._probe_browser_health(browser, timeout_ms=1234)

    assert page.goto_called is False
    assert len(page.content_calls) == 1
    html, kwargs = page.content_calls[0]
    assert "browser-ok" in html
    assert kwargs["wait_until"] == "domcontentloaded"
    assert kwargs["timeout"] == 1234
    assert context.closed is True


def test_target_closed_error_detection():
    manager = BrowserManager()
    assert manager._is_target_closed_error(RuntimeError("Target page, context or browser has been closed"))
    assert manager._is_target_closed_error(RuntimeError("Browser has been closed"))
    assert manager._is_target_closed_error(RuntimeError("browser has disconnected"))
    assert not manager._is_target_closed_error(RuntimeError("navigation timeout"))


@pytest.mark.asyncio
async def test_create_context_recovers_from_closed_browser_error(monkeypatch):
    page = _FakePage()
    context = _FakeContext(page)
    browser = _FlakyBrowser(context)
    manager = BrowserManager()

    ensure_calls = {"count": 0}
    reset_calls = {"count": 0}

    async def _fake_ensure_browser():
        ensure_calls["count"] += 1
        return browser

    async def _fake_reset_browser_state(*, stop_playwright: bool) -> None:
        _ = stop_playwright
        reset_calls["count"] += 1

    monkeypatch.setattr(manager, "_ensure_browser", _fake_ensure_browser)
    monkeypatch.setattr(manager, "_reset_browser_state", _fake_reset_browser_state)

    async with manager.create_context(timeout_ms=1500) as created_context:
        assert created_context is context

    assert ensure_calls["count"] == 2
    assert reset_calls["count"] == 1
    assert context.closed is True

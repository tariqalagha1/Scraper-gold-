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

    async def new_page(self) -> _FakePage:
        return self.page

    async def close(self) -> None:
        self.closed = True


class _FakeBrowser:
    def __init__(self, context: _FakeContext) -> None:
        self.context = context

    async def new_context(self) -> _FakeContext:
        return self.context


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

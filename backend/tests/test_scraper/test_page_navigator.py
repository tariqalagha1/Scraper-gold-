import pytest

from app.scraper.page_navigator import PageNavigator


pytestmark = pytest.mark.asyncio


class FakeElement:
    def __init__(
        self,
        href: str | None = None,
        *,
        classes: str = "",
        aria_disabled: str | None = None,
        disabled_attr: str | None = None,
        on_click=None,
    ):
        self._href = href
        self._classes = classes
        self._aria_disabled = aria_disabled
        self._disabled_attr = disabled_attr
        self._on_click = on_click

    async def count(self):
        return 1

    async def get_attribute(self, name: str):
        if name == "href":
            return self._href
        if name == "class":
            return self._classes
        if name == "aria-disabled":
            return self._aria_disabled
        if name == "disabled":
            return self._disabled_attr
        return None

    async def scroll_into_view_if_needed(self):
        return None

    async def click(self, **kwargs):
        if callable(self._on_click):
            self._on_click()
        return None


class FakeLocator:
    def __init__(self, element: FakeElement | None):
        self.first = element


class FakePage:
    def __init__(self, url: str, selectors: dict[str, FakeElement] | None = None):
        self.url = url
        self._selectors = selectors or {}
        self._signature = "sig-1"
        self._scroll_height = 100

    def locator(self, selector: str):
        element = self._selectors.get(selector)
        if element is None:
            return FakeLocator(_MissingElement())
        return FakeLocator(element)

    async def wait_for_load_state(self, state: str, timeout: int | None = None):
        return None

    async def wait_for_selector(self, selector: str, **kwargs):
        return None

    async def wait_for_timeout(self, timeout: int):
        return None

    async def evaluate(self, script: str):
        if "scrollHeight" in script:
            if "window.scrollTo" in script:
                self._scroll_height += 50
                return None
            return self._scroll_height
        if "innerText" in script:
            return self._signature
        return None


class _MissingElement:
    async def count(self):
        return 0

    async def get_attribute(self, name: str):
        return None

    async def scroll_into_view_if_needed(self):
        return None

    async def click(self, **kwargs):
        return None


async def test_page_navigator_resolves_plain_relative_next_links():
    navigator = PageNavigator()
    page = FakePage(
        "https://example.com/catalog/index.html",
        selectors={"a:has-text(\"Next\")": FakeElement("page2.html")},
    )

    result = await navigator.get_next_page(page, pagination_type="next")

    assert result == "https://example.com/catalog/page2.html"


async def test_page_navigator_click_next_returns_current_url_when_content_changes():
    page = FakePage("https://example.com/patients")

    def _advance():
        page._signature = "sig-2"

    page._selectors[".ngx-pagination .pagination-next a"] = FakeElement(
        None,
        on_click=_advance,
    )

    navigator = PageNavigator()
    result = await navigator.get_next_page(page, pagination_type="next")

    assert result == "https://example.com/patients"


async def test_page_navigator_skips_disabled_next_and_uses_numbered_link():
    page = FakePage(
        "https://example.com/patients",
        selectors={
            "a:has-text(\"Next\")": FakeElement(
                None,
                classes="disabled",
                aria_disabled="true",
            ),
            ".ngx-pagination li.current + li a": FakeElement(None, on_click=lambda: setattr(page, "_signature", "sig-2")),
        },
    )

    navigator = PageNavigator()
    result = await navigator.get_next_page(page, pagination_type="next")

    assert result == "https://example.com/patients"

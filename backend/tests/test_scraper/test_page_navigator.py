import pytest

from app.scraper.page_navigator import PageNavigator


pytestmark = pytest.mark.asyncio


class FakeElement:
    def __init__(self, href: str | None = None):
        self._href = href

    async def count(self):
        return 1

    async def get_attribute(self, name: str):
        if name == "href":
            return self._href
        return None

    async def click(self):
        return None


class FakeLocator:
    def __init__(self, element: FakeElement):
        self.first = element


class FakePage:
    def __init__(self, url: str, href: str | None):
        self.url = url
        self._href = href

    def locator(self, selector: str):
        return FakeLocator(FakeElement(self._href))

    async def wait_for_load_state(self, state: str):
        return None

    async def wait_for_selector(self, selector: str, **kwargs):
        return None


async def test_page_navigator_resolves_plain_relative_next_links():
    navigator = PageNavigator()
    page = FakePage("https://example.com/catalog/index.html", "page2.html")

    result = await navigator.get_next_page(page, pagination_type="next")

    assert result == "https://example.com/catalog/page2.html"

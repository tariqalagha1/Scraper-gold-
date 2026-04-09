from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from threading import Thread

import pytest

from app.agents.scraper_agent import ScraperAgent
from app.storage.manager import StorageManager

pytestmark = pytest.mark.asyncio


async def test_scraper_agent_captures_local_page(isolated_storage, sample_site):
    agent = ScraperAgent()

    result = await agent.safe_execute(
        {
            "url": sample_site["page_url"],
            "run_id": sample_site["run_id"],
            "config": {
                "respect_robots_txt": False,
                "wait_until": "domcontentloaded",
            },
        }
    )

    await agent.browser_manager.close()

    assert result["status"] == "success"
    assert result["data"]["html_path"]
    assert result["data"]["screenshot_path"]
    assert result["metadata"]["agent"] == "scraper_agent"
    assert result["metadata"]["source"] == sample_site["page_url"]
    assert result["metadata"]["type"] == "scraper_agent"
    assert result["metadata"]["execution_time"]

    storage = StorageManager()
    assert storage.file_exists(result["data"]["html_path"])
    assert storage.file_exists(result["data"]["screenshot_path"])


async def test_scraper_agent_honors_pagination_limits(isolated_storage, tmp_path):
    site_dir = tmp_path / "paginated-site"
    site_dir.mkdir(parents=True, exist_ok=True)
    (site_dir / "index.html").write_text(
        """
        <html>
          <body>
            <article><h2>Page One Item</h2></article>
            <a href="/page2.html">Next</a>
          </body>
        </html>
        """,
        encoding="utf-8",
    )
    (site_dir / "page2.html").write_text(
        """
        <html>
          <body>
            <article><h2>Page Two Item</h2></article>
          </body>
        </html>
        """,
        encoding="utf-8",
    )

    handler = partial(SimpleHTTPRequestHandler, directory=str(site_dir))
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    page_url = f"http://127.0.0.1:{server.server_port}/index.html"

    try:
        agent = ScraperAgent()
        result = await agent.safe_execute(
            {
                "url": page_url,
                "run_id": "pagination-run",
                "config": {
                    "respect_robots_txt": False,
                    "wait_until": "domcontentloaded",
                    "post_navigation_wait_until": "domcontentloaded",
                    "follow_pagination": True,
                    "max_pages": 2,
                },
            }
        )
        await agent.browser_manager.close()

        assert result["status"] == "success"
        assert len(result["data"]["pages"]) == 2
        assert result["data"]["pages"][0]["final_url"].endswith("/index.html")
        assert result["data"]["pages"][1]["final_url"].endswith("/page2.html")
        assert result["data"]["pages"][0]["html_path"] != result["data"]["pages"][1]["html_path"]
        assert result["data"]["pages"][0]["screenshot_path"] != result["data"]["pages"][1]["screenshot_path"]

        storage = StorageManager()
        for page in result["data"]["pages"]:
            assert storage.file_exists(page["html_path"])
            assert storage.file_exists(page["screenshot_path"])
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


async def test_scraper_agent_stops_pagination_for_detail_pages(isolated_storage, tmp_path):
    site_dir = tmp_path / "detail-site"
    site_dir.mkdir(parents=True, exist_ok=True)
    (site_dir / "index.html").write_text(
        """
        <html>
          <body>
            <article><h1>Detail Item</h1></article>
            <a href="/page2.html">Next</a>
          </body>
        </html>
        """,
        encoding="utf-8",
    )
    (site_dir / "page2.html").write_text(
        """
        <html>
          <body>
            <article><h1>Should Not Visit</h1></article>
          </body>
        </html>
        """,
        encoding="utf-8",
    )

    handler = partial(SimpleHTTPRequestHandler, directory=str(site_dir))
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    page_url = f"http://127.0.0.1:{server.server_port}/index.html"

    try:
        agent = ScraperAgent()
        result = await agent.safe_execute(
            {
                "url": page_url,
                "run_id": "detail-run",
                "strategy": {"page_type": "detail"},
                "config": {
                    "respect_robots_txt": False,
                    "wait_until": "domcontentloaded",
                    "follow_pagination": True,
                    "max_pages": 2,
                },
            }
        )
        await agent.browser_manager.close()

        assert result["status"] == "success"
        assert len(result["data"]["pages"]) == 1
        assert result["data"]["pages"][0]["final_url"].endswith("/index.html")
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


async def test_scraper_agent_uses_prompt_to_keep_single_page_runs(isolated_storage, tmp_path):
    site_dir = tmp_path / "prompt-aware-site"
    site_dir.mkdir(parents=True, exist_ok=True)
    (site_dir / "index.html").write_text(
        """
        <html>
          <body>
            <article><h2>Page One Item</h2></article>
            <a href="/page2.html">Next</a>
          </body>
        </html>
        """,
        encoding="utf-8",
    )
    (site_dir / "page2.html").write_text(
        """
        <html>
          <body>
            <article><h2>Page Two Item</h2></article>
          </body>
        </html>
        """,
        encoding="utf-8",
    )

    handler = partial(SimpleHTTPRequestHandler, directory=str(site_dir))
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    page_url = f"http://127.0.0.1:{server.server_port}/index.html"

    try:
        agent = ScraperAgent()
        result = await agent.safe_execute(
            {
                "url": page_url,
                "run_id": "prompt-single-page-run",
                "config": {
                    "respect_robots_txt": False,
                    "wait_until": "domcontentloaded",
                    "post_navigation_wait_until": "domcontentloaded",
                    "follow_pagination": True,
                    "max_pages": 2,
                    "prompt": "Extract this page only and summarize the visible content",
                },
            }
        )
        await agent.browser_manager.close()

        assert result["status"] == "success"
        assert len(result["data"]["pages"]) == 1
        assert result["data"]["pages"][0]["final_url"].endswith("/index.html")
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


async def test_scraper_agent_can_drill_into_detail_pages_from_listing(isolated_storage, tmp_path):
    site_dir = tmp_path / "detail-drill-site"
    site_dir.mkdir(parents=True, exist_ok=True)
    (site_dir / "index.html").write_text(
        """
        <html>
          <body>
            <article class="product-card"><a href="/item-1.html">Item One</a></article>
            <article class="product-card"><a href="/item-2.html">Item Two</a></article>
            <a href="/page2.html">Next</a>
          </body>
        </html>
        """,
        encoding="utf-8",
    )
    (site_dir / "item-1.html").write_text(
        """
        <html><body><main><h1>Item One Detail</h1><p>Availability: In stock</p></main></body></html>
        """,
        encoding="utf-8",
    )
    (site_dir / "item-2.html").write_text(
        """
        <html><body><main><h1>Item Two Detail</h1><p>Availability: Low stock</p></main></body></html>
        """,
        encoding="utf-8",
    )
    (site_dir / "page2.html").write_text(
        """
        <html><body><article class="product-card"><a href="/item-3.html">Item Three</a></article></body></html>
        """,
        encoding="utf-8",
    )

    handler = partial(SimpleHTTPRequestHandler, directory=str(site_dir))
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    page_url = f"http://127.0.0.1:{server.server_port}/index.html"

    try:
        agent = ScraperAgent()
        result = await agent.safe_execute(
            {
                "url": page_url,
                "run_id": "detail-drill-run",
                "strategy": {
                    "page_type": "list",
                    "record_fields": ["title", "availability", "link"],
                    "selectors": {
                        "container": ".product-card",
                        "fields": {
                            "link": ".product-card a[href]",
                        },
                    },
                },
                "config": {
                    "respect_robots_txt": False,
                    "wait_until": "domcontentloaded",
                    "post_navigation_wait_until": "domcontentloaded",
                    "max_pages": 3,
                    "prompt": "Visit each product page and collect availability details",
                    "follow_detail_pages": True,
                    "detail_link_selector": ".product-card a[href]",
                },
            }
        )
        await agent.browser_manager.close()

        assert result["status"] == "success"
        assert len(result["data"]["pages"]) == 3
        assert result["data"]["pages"][0]["final_url"].endswith("/index.html")
        assert result["data"]["pages"][1]["final_url"].endswith("/item-1.html")
        assert result["data"]["pages"][2]["final_url"].endswith("/item-2.html")
        assert all(not page["final_url"].endswith("/page2.html") for page in result["data"]["pages"])
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


async def test_scraper_agent_respects_detail_page_limit(isolated_storage, tmp_path):
    site_dir = tmp_path / "detail-budget-site"
    site_dir.mkdir(parents=True, exist_ok=True)
    (site_dir / "index.html").write_text(
        """
        <html>
          <body>
            <article class="product-card"><a href="/item-1.html">Item One</a></article>
            <article class="product-card"><a href="/item-2.html">Item Two</a></article>
            <article class="product-card"><a href="/item-3.html">Item Three</a></article>
          </body>
        </html>
        """,
        encoding="utf-8",
    )
    for index in range(1, 4):
        (site_dir / f"item-{index}.html").write_text(
            f"""
            <html><body><main><h1>Item {index} Detail</h1><p>Availability: In stock</p></main></body></html>
            """,
            encoding="utf-8",
        )

    handler = partial(SimpleHTTPRequestHandler, directory=str(site_dir))
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    page_url = f"http://127.0.0.1:{server.server_port}/index.html"

    try:
        agent = ScraperAgent()
        result = await agent.safe_execute(
            {
                "url": page_url,
                "run_id": "detail-budget-run",
                "strategy": {
                    "page_type": "list",
                    "record_fields": ["title", "availability", "link"],
                    "selectors": {
                        "container": ".product-card",
                        "fields": {
                            "link": ".product-card a[href]",
                        },
                    },
                },
                "config": {
                    "respect_robots_txt": False,
                    "wait_until": "domcontentloaded",
                    "post_navigation_wait_until": "domcontentloaded",
                    "max_pages": 6,
                    "traversal_mode": "detail_drill",
                    "detail_page_limit": 2,
                    "detail_link_selector": ".product-card a[href]",
                },
            }
        )
        await agent.browser_manager.close()

        assert result["status"] == "success"
        assert len(result["data"]["pages"]) == 3
        assert result["data"]["pages"][0]["final_url"].endswith("/index.html")
        assert result["data"]["pages"][1]["final_url"].endswith("/item-1.html")
        assert result["data"]["pages"][2]["final_url"].endswith("/item-2.html")
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


async def test_scraper_agent_stops_detail_drill_on_duplicate_title(isolated_storage, tmp_path):
    site_dir = tmp_path / "duplicate-detail-site"
    site_dir.mkdir(parents=True, exist_ok=True)
    (site_dir / "index.html").write_text(
        """
        <html>
          <body>
            <article class="product-card"><a href="/item-1.html">Item One</a></article>
            <article class="product-card"><a href="/item-2.html">Item Two</a></article>
            <article class="product-card"><a href="/item-3.html">Item Three</a></article>
          </body>
        </html>
        """,
        encoding="utf-8",
    )
    (site_dir / "item-1.html").write_text(
        """
        <html><body><main><h1>Repeated Detail</h1><p>Availability: In stock</p></main></body></html>
        """,
        encoding="utf-8",
    )
    (site_dir / "item-2.html").write_text(
        """
        <html><body><main><h1>Repeated Detail</h1><p>Availability: Still in stock</p></main></body></html>
        """,
        encoding="utf-8",
    )
    (site_dir / "item-3.html").write_text(
        """
        <html><body><main><h1>Unique Detail</h1><p>Availability: Low stock</p></main></body></html>
        """,
        encoding="utf-8",
    )

    handler = partial(SimpleHTTPRequestHandler, directory=str(site_dir))
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    page_url = f"http://127.0.0.1:{server.server_port}/index.html"

    try:
        agent = ScraperAgent()
        result = await agent.safe_execute(
            {
                "url": page_url,
                "run_id": "duplicate-detail-run",
                "strategy": {
                    "page_type": "list",
                    "record_fields": ["title", "availability", "link"],
                    "selectors": {
                        "container": ".product-card",
                        "fields": {
                            "link": ".product-card a[href]",
                        },
                    },
                },
                "config": {
                    "respect_robots_txt": False,
                    "wait_until": "domcontentloaded",
                    "post_navigation_wait_until": "domcontentloaded",
                    "max_pages": 6,
                    "traversal_mode": "detail_drill",
                    "detail_page_limit": 3,
                    "detail_stop_rule": "duplicate_title",
                    "detail_link_selector": ".product-card a[href]",
                },
            }
        )
        await agent.browser_manager.close()

        assert result["status"] == "success"
        assert len(result["data"]["pages"]) == 2
        assert result["data"]["pages"][0]["final_url"].endswith("/index.html")
        assert result["data"]["pages"][1]["final_url"].endswith("/item-1.html")
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


async def test_scraper_agent_prefers_list_harvest_over_detail_drill_when_requested(isolated_storage, tmp_path):
    site_dir = tmp_path / "list-harvest-site"
    site_dir.mkdir(parents=True, exist_ok=True)
    (site_dir / "index.html").write_text(
        """
        <html>
          <body>
            <article class="product-card"><a href="/item-1.html">Item One</a></article>
            <article class="product-card"><a href="/item-2.html">Item Two</a></article>
            <a href="/page2.html">Next</a>
          </body>
        </html>
        """,
        encoding="utf-8",
    )
    (site_dir / "page2.html").write_text(
        """
        <html><body><article class="product-card"><a href="/item-3.html">Page Two Listing</a></article></body></html>
        """,
        encoding="utf-8",
    )
    (site_dir / "item-1.html").write_text(
        """
        <html><body><main><h1>Item One Detail</h1><p>Availability: In stock</p></main></body></html>
        """,
        encoding="utf-8",
    )
    (site_dir / "item-2.html").write_text(
        """
        <html><body><main><h1>Item Two Detail</h1><p>Availability: Low stock</p></main></body></html>
        """,
        encoding="utf-8",
    )

    handler = partial(SimpleHTTPRequestHandler, directory=str(site_dir))
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    page_url = f"http://127.0.0.1:{server.server_port}/index.html"

    try:
        agent = ScraperAgent()
        result = await agent.safe_execute(
            {
                "url": page_url,
                "run_id": "list-harvest-run",
                "strategy": {
                    "page_type": "list",
                    "record_fields": ["title", "price", "link"],
                    "selectors": {
                        "container": ".product-card",
                        "fields": {
                            "link": ".product-card a[href]",
                        },
                    },
                },
                "config": {
                    "respect_robots_txt": False,
                    "wait_until": "domcontentloaded",
                    "post_navigation_wait_until": "domcontentloaded",
                    "max_pages": 2,
                    "prompt": "Collect the visible product list and follow pagination",
                    "follow_pagination": True,
                    "traversal_mode": "list_harvest",
                },
            }
        )
        await agent.browser_manager.close()

        assert result["status"] == "success"
        assert len(result["data"]["pages"]) == 2
        assert result["data"]["pages"][0]["final_url"].endswith("/index.html")
        assert result["data"]["pages"][1]["final_url"].endswith("/page2.html")
        assert all("/item-" not in page["final_url"] for page in result["data"]["pages"])
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)

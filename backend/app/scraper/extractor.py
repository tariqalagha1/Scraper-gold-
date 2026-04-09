from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any, Optional
from urllib.parse import urljoin
import re

from bs4 import BeautifulSoup

from app.core.logging import get_logger
from app.schemas.scraping_types import ScrapingType
from app.scraper.extraction_confidence import (
    collection_confidence,
    list_confidence,
    text_confidence,
)
from app.scraper.extraction_patterns import (
    classify_file_type,
    is_probable_image,
    is_probable_video,
    normalize_href,
)


logger = get_logger("app.scraper.extractor")

if TYPE_CHECKING:
    from playwright.async_api import Page


class ContentExtractor:
    def extract(
        self,
        *,
        raw_html: str,
        url: str,
        scraping_type: str | ScrapingType = ScrapingType.GENERAL,
        selectors: Optional[dict[str, str]] = None,
    ) -> dict[str, Any]:
        selectors = selectors or {}
        scrape_type = self._normalize_scrape_type(scraping_type)
        soup = BeautifulSoup(raw_html or "", "lxml")

        title_value = self._extract_title(soup, selectors)
        headings = self._extract_headings(soup, selectors)
        paragraphs = self._extract_paragraphs(soup, selectors)
        links = self._extract_links(soup, url, selectors)
        files = self._extract_files(links)
        images = self._extract_images(soup, url, selectors)
        videos = self._extract_videos(soup, url, selectors, links)
        tables = self._extract_tables(soup, selectors)
        lists = self._extract_lists(soup, selectors)
        records, selector_used = self._extract_structured_records(soup, url, selectors)

        if selector_used:
            logger.info(
                "Structured list extraction completed.",
                selector_used=selector_used,
                records=len(records),
            )

        data: dict[str, Any] = {
            "title": {
                "value": title_value,
                "confidence": text_confidence(title_value, preferred_source="title"),
            },
            "headings": headings if scrape_type in {ScrapingType.GENERAL, ScrapingType.STRUCTURED} else [],
            "paragraphs": paragraphs if scrape_type == ScrapingType.GENERAL else [],
            "links": links if scrape_type == ScrapingType.GENERAL else [],
            "files": self._filter_files_by_type(files, scrape_type),
            "images": images if scrape_type in {ScrapingType.GENERAL, ScrapingType.IMAGES} else [],
            "videos": videos if scrape_type in {ScrapingType.GENERAL, ScrapingType.VIDEOS} else [],
            "tables": tables if scrape_type in {ScrapingType.GENERAL, ScrapingType.STRUCTURED} else [],
            "lists": lists if scrape_type in {ScrapingType.GENERAL, ScrapingType.STRUCTURED} else [],
            "records": records,
        }

        return {
            "status": "success",
            "data": data,
            "error": None,
            "metadata": {
                "source_url": url,
                "scraping_type": scrape_type.value,
                "parser": "beautifulsoup+lxml",
                "selector_used": selector_used,
                "records_extracted": len(records),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
        }

    async def extract_from_page(
        self,
        *,
        page: Page,
        url: str,
        scraping_type: str | ScrapingType = ScrapingType.GENERAL,
        selectors: Optional[dict[str, str]] = None,
    ) -> dict[str, Any]:
        raw_html = await page.content()
        return self.extract(
            raw_html=raw_html,
            url=url,
            scraping_type=scraping_type,
            selectors=selectors,
        )

    def _normalize_scrape_type(self, scraping_type: str | ScrapingType) -> ScrapingType:
        if isinstance(scraping_type, ScrapingType):
            return scraping_type
        try:
            return ScrapingType(scraping_type.lower())
        except Exception:
            return ScrapingType.GENERAL

    def _select_many(self, soup: BeautifulSoup, selector: Optional[str], fallback: str) -> list[Any]:
        if selector:
            selected = soup.select(selector)
            if selected:
                return selected
        return soup.select(fallback)

    def _extract_title(self, soup: BeautifulSoup, selectors: dict[str, str]) -> str:
        title_selector = selectors.get("title")
        if title_selector:
            nodes = soup.select(title_selector)
            if nodes:
                value = nodes[0].get_text(" ", strip=True)
                if value:
                    return value

        for selector in ("meta[property='og:title']", "meta[name='twitter:title']"):
            node = soup.select_one(selector)
            if node and node.get("content"):
                return node["content"].strip()

        if soup.title and soup.title.string:
            return soup.title.string.strip()

        first_heading = soup.select_one("h1, h2")
        return first_heading.get_text(" ", strip=True) if first_heading else ""

    def _extract_headings(self, soup: BeautifulSoup, selectors: dict[str, str]) -> list[dict[str, Any]]:
        nodes = self._select_many(soup, selectors.get("headings"), "h1, h2, h3, h4, h5, h6")
        items: list[dict[str, Any]] = []
        for node in nodes:
            text = node.get_text(" ", strip=True)
            if not text:
                continue
            items.append(
                {
                    "value": text,
                    "level": getattr(node, "name", ""),
                    "confidence": text_confidence(text, preferred_source="heading"),
                }
            )
        return items

    def _extract_paragraphs(self, soup: BeautifulSoup, selectors: dict[str, str]) -> list[dict[str, Any]]:
        nodes = self._select_many(soup, selectors.get("paragraphs"), "p")
        items: list[dict[str, Any]] = []
        for node in nodes:
            text = node.get_text(" ", strip=True)
            if len(text) < 20:
                continue
            items.append(
                {
                    "value": text,
                    "confidence": text_confidence(text, preferred_source="paragraph"),
                }
            )
        return items

    def _extract_links(self, soup: BeautifulSoup, base_url: str, selectors: dict[str, str]) -> list[dict[str, Any]]:
        nodes = self._select_many(soup, selectors.get("links"), "a[href]")
        results: list[dict[str, Any]] = []
        seen: set[str] = set()
        for node in nodes:
            href = normalize_href(node.get("href"))
            if not href:
                continue
            absolute_url = urljoin(base_url, href)
            if absolute_url in seen:
                continue
            seen.add(absolute_url)
            text = node.get_text(" ", strip=True)
            results.append(
                {
                    "url": absolute_url,
                    "text": text,
                    "confidence": collection_confidence(
                        value=absolute_url,
                        text_hint=text,
                        source_tag="a",
                    ),
                }
            )
        return results

    def _extract_files(self, links: list[dict[str, Any]]) -> list[dict[str, Any]]:
        files: list[dict[str, Any]] = []
        for link in links:
            file_type = classify_file_type(link["url"])
            if not file_type:
                continue
            files.append(
                {
                    "url": link["url"],
                    "name": link["text"] or link["url"].split("/")[-1],
                    "type": file_type,
                    "confidence": collection_confidence(
                        value=link["url"],
                        text_hint=link.get("text", ""),
                        source_tag="file",
                    ),
                }
            )
        return files

    def _extract_images(
        self,
        soup: BeautifulSoup,
        base_url: str,
        selectors: dict[str, str],
    ) -> list[dict[str, Any]]:
        nodes = self._select_many(soup, selectors.get("images"), "img[src], source[srcset]")
        results: list[dict[str, Any]] = []
        seen: set[str] = set()
        for node in nodes:
            raw_value = node.get("src") or node.get("data-src") or self._first_srcset(node.get("srcset"))
            if not raw_value:
                continue
            absolute_url = urljoin(base_url, raw_value)
            if absolute_url in seen or not is_probable_image(absolute_url, node.name):
                continue
            seen.add(absolute_url)
            alt = node.get("alt", "")
            results.append(
                {
                    "url": absolute_url,
                    "alt": alt,
                    "confidence": collection_confidence(
                        value=absolute_url,
                        text_hint=alt,
                        source_tag=node.name or "img",
                    ),
                }
            )
        return results

    def _extract_videos(
        self,
        soup: BeautifulSoup,
        base_url: str,
        selectors: dict[str, str],
        links: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        results: list[dict[str, Any]] = []
        seen: set[str] = set()

        nodes = self._select_many(soup, selectors.get("videos"), "video[src], video source[src], iframe[src]")
        for node in nodes:
            src = node.get("src") or self._first_srcset(node.get("srcset"))
            if not src:
                continue
            absolute_url = urljoin(base_url, src)
            if absolute_url in seen or not is_probable_video(absolute_url, node.name):
                continue
            seen.add(absolute_url)
            results.append(
                {
                    "url": absolute_url,
                    "confidence": collection_confidence(
                        value=absolute_url,
                        text_hint="",
                        source_tag=node.name or "video",
                    ),
                }
            )

        for link in links:
            if link["url"] in seen or not is_probable_video(link["url"], "a"):
                continue
            seen.add(link["url"])
            results.append(
                {
                    "url": link["url"],
                    "confidence": collection_confidence(
                        value=link["url"],
                        text_hint=link.get("text", ""),
                        source_tag="a",
                    ),
                }
            )
        return results

    def _extract_tables(self, soup: BeautifulSoup, selectors: dict[str, str]) -> list[dict[str, Any]]:
        nodes = self._select_many(soup, selectors.get("tables"), "table")
        tables: list[dict[str, Any]] = []
        for index, table in enumerate(nodes):
            rows = []
            for row in table.select("tr"):
                cells = [cell.get_text(" ", strip=True) for cell in row.select("th, td")]
                if any(cells):
                    rows.append(cells)
            if not rows:
                continue
            tables.append(
                {
                    "index": index,
                    "rows": rows,
                    "confidence": list_confidence(rows),
                }
            )
        return tables

    def _extract_lists(self, soup: BeautifulSoup, selectors: dict[str, str]) -> list[dict[str, Any]]:
        nodes = self._select_many(soup, selectors.get("lists"), "ul, ol")
        lists: list[dict[str, Any]] = []
        for node in nodes:
            items = [item.get_text(" ", strip=True) for item in node.select("li")]
            items = [item for item in items if item]
            if not items:
                continue
            lists.append(
                {
                    "type": node.name,
                    "items": items,
                    "confidence": list_confidence(items),
                }
            )
        return lists

    def _extract_structured_records(
        self,
        soup: BeautifulSoup,
        base_url: str,
        selectors: dict[str, Any],
    ) -> tuple[list[dict[str, Any]], str | None]:
        field_selectors = selectors.get("fields", {}) if isinstance(selectors.get("fields"), dict) else {}
        table_selectors = {"table tbody tr", "table tr", "[role='row']"}
        table_structures_detected = False

        for selector in self._container_candidates(selectors):
            nodes = soup.select(selector)
            logger.info("Structured list selector scanned.", selector_used=selector, containers_found=len(nodes))
            if not nodes:
                continue
            if selector in table_selectors:
                table_structures_detected = True
            # If tabular structures are present but yielded no valid row records,
            # avoid falling back to menu/list links on the same page.
            if table_structures_detected and selector in {"li", "a[href]"}:
                continue

            records = self._deduplicate_records(
                [
                    record
                    for record in (
                        self._extract_record_from_container(node, selector, field_selectors, base_url)
                        for node in nodes
                    )
                    if record
                ]
            )
            logger.info(
                "Structured list selector evaluated.",
                selector_used=selector,
                containers_found=len(nodes),
                records=len(records),
            )

            if len(records) >= 5:
                return records, selector
            if records:
                return records, selector

        return [], None

    def _container_candidates(self, selectors: dict[str, Any]) -> list[str]:
        seen: set[str] = set()
        candidates: list[str] = []

        def add(selector: str) -> None:
            normalized = selector.strip()
            if not normalized or normalized in seen:
                return
            seen.add(normalized)
            candidates.append(normalized)

        add("article.product_pod")

        configured_container = selectors.get("container")
        if isinstance(configured_container, str):
            for selector in configured_container.split(","):
                add(selector)

        # Prefer table rows before generic list/link containers so admin/data
        # grids (patients, invoices, etc.) are parsed as records first.
        for selector in ("table tbody tr", "table tr", "[role='row']", "article", ".product", "li", "a[href]"):
            add(selector)

        return candidates

    def _extract_record_from_container(
        self,
        node: Any,
        selector_used: str,
        field_selectors: dict[str, Any],
        base_url: str,
    ) -> dict[str, Any] | None:
        if self._is_table_row(node, selector_used):
            item = self._extract_record_from_table_row(node)
            return item if self._is_valid_record(item) else None

        if selector_used == "a[href]":
            href = normalize_href(node.get("href"))
            item = {
                "title": node.get_text(" ", strip=True),
                "price": "",
                "link": urljoin(base_url, href) if href else "",
            }
            return item if self._is_valid_record(item) else None

        title = self._text_from_node(
            node,
            self._pick_selector(field_selectors.get("title"), "h3 a, h2 a, h1 a, h3, h2, h1, a[href]"),
        )
        link = self._href_from_node(
            node,
            self._pick_selector(field_selectors.get("link"), "h3 a[href], h2 a[href], h1 a[href], a[href]"),
            base_url,
        )
        price = self._text_from_node(
            node,
            self._pick_selector(field_selectors.get("price"), ".price_color, .price, [itemprop='price']"),
        )

        item = {
            "title": title,
            "price": price,
            "link": link,
        }
        for field_name, selector in field_selectors.items():
            normalized_field = str(field_name).strip()
            if not normalized_field or normalized_field in item:
                continue
            item[normalized_field] = self._extract_field_value(
                node=node,
                field_name=normalized_field,
                selector=selector,
                base_url=base_url,
            )
        return item if self._is_valid_record(item) else None

    def _is_table_row(self, node: Any, selector_used: str) -> bool:
        selector = str(selector_used or "").lower()
        node_name = str(getattr(node, "name", "") or "").lower()
        return node_name == "tr" or "tr" in selector or "role='row'" in selector or 'role="row"' in selector

    def _extract_record_from_table_row(self, node: Any) -> dict[str, Any]:
        if node.select("th") and not node.select("td"):
            return {"title": "", "price": "", "link": ""}

        table = node.find_parent("table")
        # Skip small key-value/detail tables and keep list/grid tables only.
        if len(self._table_data_rows(table)) < 3:
            return {"title": "", "price": "", "link": ""}

        cells = [cell.get_text(" ", strip=True) for cell in node.select("td, th")]
        cells = [cell for cell in cells if cell]
        # Ignore key-value detail tables (common in modals) and focus on
        # grid-like rows with multiple columns.
        if len(cells) < 4:
            return {"title": "", "price": "", "link": ""}

        headers = self._table_headers(table)

        details: dict[str, str] = {}
        if headers and len(headers) >= len(cells):
            for index, value in enumerate(cells):
                header = headers[index] if index < len(headers) else f"column_{index + 1}"
                normalized_key = self._normalize_field_key(header) or f"column_{index + 1}"
                if normalized_key in details:
                    normalized_key = f"{normalized_key}_{index + 1}"
                details[normalized_key] = value
        else:
            details = {
                f"column_{index + 1}": value
                for index, value in enumerate(cells)
            }

        title = (
            details.get("name")
            or details.get("patient_name")
            or details.get("full_name")
            or details.get("registration_no")
            or cells[0]
        )
        link_node = node.select_one("a[href]")
        link = normalize_href(link_node.get("href")) if link_node else ""

        return {
            "title": title,
            "price": "",
            "link": link,
            **details,
        }

    def _table_headers(self, table: Any) -> list[str]:
        if table is None:
            return []
        header_row = table.select_one("thead tr") or table.select_one("tr")
        if header_row is None:
            return []
        headers = [cell.get_text(" ", strip=True) for cell in header_row.select("th, td")]
        return [header for header in headers if header]

    def _table_data_rows(self, table: Any) -> list[Any]:
        if table is None:
            return []
        rows = table.select("tbody tr")
        if not rows:
            rows = table.select("tr")
        data_rows: list[Any] = []
        for row in rows:
            if not row.select("td"):
                continue
            cells = [cell.get_text(" ", strip=True) for cell in row.select("td")]
            if any(cells):
                data_rows.append(row)
        return data_rows

    def _normalize_field_key(self, value: str) -> str:
        lowered = str(value or "").strip().lower()
        if not lowered:
            return ""
        normalized = re.sub(r"[^a-z0-9]+", "_", lowered).strip("_")
        return normalized

    def _pick_selector(self, configured: Any, fallback: str) -> str:
        return configured.strip() if isinstance(configured, str) and configured.strip() else fallback

    def _extract_field_value(
        self,
        *,
        node: Any,
        field_name: str,
        selector: Any,
        base_url: str,
    ) -> str:
        chosen_selector = selector.strip() if isinstance(selector, str) and selector.strip() else ""
        target = node.select_one(chosen_selector) if chosen_selector else None
        target = target or node
        normalized_field = field_name.strip().lower()
        if normalized_field in {"link", "url", "href"}:
            return self._href_from_node(node, chosen_selector or "a[href]", base_url)
        if target and target.get("content"):
            return str(target.get("content")).strip()
        return target.get_text(" ", strip=True) if target else ""

    def _text_from_node(self, node: Any, selector: str) -> str:
        target = node.select_one(selector) if selector else None
        target = target or node
        return target.get_text(" ", strip=True) if target else ""

    def _href_from_node(self, node: Any, selector: str, base_url: str) -> str:
        target = node.select_one(selector) if selector else None
        href = normalize_href(target.get("href") if target else "")
        return urljoin(base_url, href) if href else ""

    def _is_valid_record(self, item: dict[str, Any]) -> bool:
        return bool(str(item.get("title") or "").strip() or str(item.get("link") or "").strip())

    def _deduplicate_records(self, items: list[dict[str, Any]]) -> list[dict[str, Any]]:
        seen: set[tuple[str, str]] = set()
        normalized: list[dict[str, Any]] = []

        for item in items:
            title = str(item.get("title") or "").strip()
            link = str(item.get("link") or "").strip()
            key = (title.lower(), link.lower())
            if key in seen:
                continue
            seen.add(key)
            normalized.append(
                {
                    "title": title,
                    "price": str(item.get("price") or "").strip(),
                    "link": link,
                    **{
                        str(key): str(value).strip()
                        for key, value in item.items()
                        if str(key) not in {"title", "price", "link"}
                        and str(value).strip()
                    },
                }
            )

        return normalized

    def _filter_files_by_type(
        self,
        files: list[dict[str, Any]],
        scrape_type: ScrapingType,
    ) -> list[dict[str, Any]]:
        if scrape_type == ScrapingType.PDF:
            return [file for file in files if file["type"] == "pdf"]
        if scrape_type == ScrapingType.WORD:
            return [file for file in files if file["type"] == "word"]
        if scrape_type == ScrapingType.EXCEL:
            return [file for file in files if file["type"] == "excel"]
        if scrape_type == ScrapingType.GENERAL:
            return files
        return []

    def _first_srcset(self, srcset: Optional[str]) -> str:
        if not srcset:
            return ""
        return srcset.split(",")[0].strip().split(" ")[0].strip()

from __future__ import annotations

import re
from html import unescape
from typing import Any
from urllib.parse import urljoin

import bleach
from bs4 import BeautifulSoup, Tag


_SCRIPT_STYLE_BLOCK_RE = re.compile(
    r"<\s*(script|style)\b[^>]*>.*?<\s*/\s*\1\s*>",
    re.IGNORECASE | re.DOTALL,
)
_JS_PROTOCOL_RE = re.compile(r"(?i)\b(?:javascript|vbscript|data)\s*:")
_SEMANTIC_JUNK_SELECTORS = (
    "nav",
    "header",
    "footer",
    "aside",
    "form",
    "noscript",
    "iframe",
    "svg",
    "canvas",
    "[role='navigation']",
    "[role='banner']",
    "[role='contentinfo']",
    "[aria-label*='breadcrumb' i]",
    ".breadcrumb",
    ".breadcrumbs",
    ".navbar",
    ".nav",
    ".sidebar",
    ".menu",
    ".pagination",
)
_SEMANTIC_BLOCK_TAGS = ("h1", "h2", "h3", "h4", "h5", "h6", "p", "li", "blockquote", "pre", "code", "table")


def sanitize_untrusted_html(value: str) -> str:
    """Neutralize untrusted HTML/JS content from scraped text.

    This strips dangerous blocks (for example <script>...</script>), removes
    all HTML tags and attributes (including inline handlers like onload/onerror),
    and neutralizes dangerous script-like protocols that may remain as text.
    """
    raw = str(value or "")
    without_script_blocks = _SCRIPT_STYLE_BLOCK_RE.sub(" ", raw)
    no_html = bleach.clean(
        without_script_blocks,
        tags=[],
        attributes={},
        protocols=[],
        strip=True,
        strip_comments=True,
    )
    return _JS_PROTOCOL_RE.sub("", no_html)


def clean_text(value: str) -> str:
    text = sanitize_untrusted_html(unescape(value or ""))
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _is_nested_semantic_block(element: Tag) -> bool:
    parent = element.parent
    while isinstance(parent, Tag):
        if parent.name in _SEMANTIC_BLOCK_TAGS:
            return True
        parent = parent.parent
    return False


def _table_to_markdown(table: Tag) -> str:
    rows: list[list[str]] = []
    for row in table.find_all("tr"):
        cells = [clean_text(cell.get_text(" ", strip=True)) for cell in row.find_all(["th", "td"])]
        if any(cells):
            rows.append(cells)
    if not rows:
        return ""

    width = max(len(row) for row in rows)
    normalized_rows = [row + [""] * (width - len(row)) for row in rows]
    header = normalized_rows[0]
    divider = ["---"] * width
    body = normalized_rows[1:]
    markdown_rows = [header, divider, *body]
    return "\n".join(f"| {' | '.join(row)} |" for row in markdown_rows)


def _element_to_markdown(element: Tag) -> str:
    name = str(element.name or "").lower()
    text = clean_text(element.get_text(" ", strip=True))
    if not text and name != "table":
        return ""

    if name.startswith("h") and len(name) == 2 and name[1].isdigit():
        level = max(1, min(6, int(name[1])))
        return f"{'#' * level} {text}"
    if name == "li":
        return f"- {text}"
    if name == "blockquote":
        return f"> {text}"
    if name in {"pre", "code"}:
        return f"```\n{text}\n```" if text else ""
    if name == "table":
        return _table_to_markdown(element)
    return text


def html_to_semantic_markdown(raw_html: str, *, max_chars: int = 60_000) -> str:
    """Convert raw HTML to compact semantic Markdown for LLM-oriented parsing."""
    soup = BeautifulSoup(str(raw_html or ""), "lxml")

    for tag_name in ("script", "style", "template"):
        for node in soup.find_all(tag_name):
            node.decompose()
    for selector in _SEMANTIC_JUNK_SELECTORS:
        for node in soup.select(selector):
            node.decompose()

    root = soup.select_one("main, article, [role='main'], #content, .content, #main, .main") or soup.body or soup
    parts: list[str] = []
    seen: set[str] = set()

    title_node = soup.title.get_text(" ", strip=True) if soup.title else ""
    title_text = clean_text(title_node)
    if title_text:
        title_line = f"# {title_text}"
        parts.append(title_line)
        seen.add(title_line.lower())

    total_chars = sum(len(part) for part in parts)
    for element in root.find_all(_SEMANTIC_BLOCK_TAGS):
        if _is_nested_semantic_block(element):
            continue
        markdown_block = _element_to_markdown(element)
        if not markdown_block:
            continue
        key = markdown_block.strip().lower()
        if key in seen:
            continue
        seen.add(key)
        parts.append(markdown_block)
        total_chars += len(markdown_block)
        if total_chars >= max_chars:
            break

    markdown = "\n\n".join(parts).strip()
    markdown = re.sub(r"\n{3,}", "\n\n", markdown)
    if len(markdown) > max_chars:
        markdown = markdown[:max_chars].rstrip()
    return markdown


def deduplicate_by_url(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[str] = set()
    normalized: list[dict[str, Any]] = []
    for item in items:
        url = clean_text(item.get("url", ""))
        if not url or url in seen:
            continue
        seen.add(url)
        normalized.append(item)
    return normalized


def normalize_link_item(item: dict[str, Any], base_url: str) -> dict[str, Any]:
    url = urljoin(base_url, clean_text(item.get("url", "")))
    return {
        "url": url,
        "text": clean_text(item.get("text", "")),
        "confidence": float(item.get("confidence", 0.0)),
    }


def normalize_file_item(item: dict[str, Any], base_url: str) -> dict[str, Any]:
    url = urljoin(base_url, clean_text(item.get("url", "")))
    return {
        "url": url,
        "name": clean_text(item.get("name", "")) or url.split("/")[-1],
        "type": clean_text(item.get("type", "")).lower(),
        "confidence": float(item.get("confidence", 0.0)),
    }


def normalize_table_item(item: dict[str, Any]) -> dict[str, Any]:
    rows = item.get("rows", [])
    if not isinstance(rows, list):
        rows = []

    cleaned_rows: list[list[str]] = []
    for row in rows:
        if isinstance(row, list):
            cleaned_rows.append([clean_text(cell) for cell in row])

    columns = cleaned_rows[0] if cleaned_rows else []
    data_rows = cleaned_rows[1:] if len(cleaned_rows) > 1 else []

    return {
        "columns": columns,
        "rows": data_rows,
        "confidence": float(item.get("confidence", 0.0)),
    }


def classify_page_type(
    *,
    title: str,
    cleaned_text: str,
    files: list[dict[str, Any]],
    images: list[dict[str, Any]],
    tables: list[dict[str, Any]],
    links: list[dict[str, Any]],
) -> str:
    lowered = f"{title} {cleaned_text}".lower()
    if files:
        file_types = {file.get("type", "") for file in files}
        if "pdf" in file_types:
            return "document_repository"
        if "word" in file_types or "excel" in file_types:
            return "file_listing"
    if tables:
        return "structured_data_page"
    if images and len(images) >= max(3, len(links) // 2):
        return "media_gallery"
    if any(keyword in lowered for keyword in ("product", "price", "buy", "cart")):
        return "product_page"
    if any(keyword in lowered for keyword in ("article", "blog", "news", "posted")):
        return "article_page"
    if links and not cleaned_text:
        return "link_directory"
    return "general_page"


def build_summary(
    *,
    title: str,
    cleaned_text: str,
    page_type: str,
    files: list[dict[str, Any]],
    images: list[dict[str, Any]],
    tables: list[dict[str, Any]],
    links: list[dict[str, Any]],
) -> str:
    lead = clean_text(title) or "Untitled page"
    body = clean_text(cleaned_text)
    snippet = " ".join(body.split()[:40])
    parts = [
        lead,
        f"Type: {page_type.replace('_', ' ')}.",
        f"Links: {len(links)}.",
        f"Files: {len(files)}.",
        f"Images: {len(images)}.",
        f"Tables: {len(tables)}.",
    ]
    if snippet:
        parts.append(snippet)
    return clean_text(" ".join(parts))

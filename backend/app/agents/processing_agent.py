from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from urllib.parse import urljoin

from app.agents.base_agent import BaseAgent
from app.scraper.processing_helpers import (
    build_summary,
    classify_page_type,
    clean_text,
    deduplicate_by_url,
    normalize_file_item,
    normalize_link_item,
    normalize_table_item,
)


class ProcessingAgent(BaseAgent):
    def __init__(self) -> None:
        super().__init__(agent_name="processing_agent")

    async def execute(self, input_data: dict[str, Any]) -> dict[str, Any]:
        extracted = self._resolve_extracted_payload(input_data)
        if not isinstance(extracted, dict):
            return self._failure_payload("Input must include extracted JSON payload.")

        status = extracted.get("status", "success")
        if status != "success":
            return self._failure_payload(extracted.get("error", "Extractor payload is not successful."))

        data = extracted.get("data", {})
        if not isinstance(data, dict):
            return self._failure_payload("Extractor payload data must be an object.")

        source_url = self._resolve_source_url(input_data, extracted, data)
        semantic_markdown = self._resolve_semantic_markdown(input_data)
        structured_records = self._normalize_structured_records(data.get("records", []), source_url)

        title_value = self._safe_text(data.get("title", {}).get("value") if isinstance(data.get("title"), dict) else "")
        cleaned_paragraphs = [
            {"value": clean_text(item.get("value", "")), "confidence": float(item.get("confidence", 0.0))}
            for item in data.get("paragraphs", [])
            if isinstance(item, dict) and clean_text(item.get("value", ""))
        ]
        cleaned_headings = [
            {
                "value": clean_text(item.get("value", "")),
                "level": self._safe_text(item.get("level", "")),
                "confidence": float(item.get("confidence", 0.0)),
            }
            for item in data.get("headings", [])
            if isinstance(item, dict) and clean_text(item.get("value", ""))
        ]

        cleaned_text = clean_text(
            " ".join(
                part
                for part in [
                    title_value,
                    " ".join(item["value"] for item in cleaned_headings),
                    " ".join(item["value"] for item in cleaned_paragraphs),
                ]
                if part
            )
        )
        if semantic_markdown:
            markdown_fallback = clean_text(semantic_markdown[:12_000])
            if len(markdown_fallback) > len(cleaned_text):
                cleaned_text = markdown_fallback

        normalized_links = deduplicate_by_url(
            [
                normalize_link_item(item, source_url)
                for item in data.get("links", [])
                if isinstance(item, dict)
            ]
        )
        normalized_files = deduplicate_by_url(
            [
                normalize_file_item(item, source_url)
                for item in data.get("files", [])
                if isinstance(item, dict)
            ]
        )
        normalized_images = deduplicate_by_url(
            [
                {
                    "url": urljoin(source_url, self._safe_text(item.get("url", ""))),
                    "alt": self._safe_text(item.get("alt", "")),
                    "confidence": float(item.get("confidence", 0.0)),
                }
                for item in data.get("images", [])
                if isinstance(item, dict) and self._safe_text(item.get("url", ""))
            ]
        )
        normalized_tables = [
            normalize_table_item(item)
            for item in data.get("tables", [])
            if isinstance(item, dict)
        ]

        if structured_records:
            cleaned_text = clean_text(" ".join(record.get("content", "") for record in structured_records))
            summary = f"Extracted {len(structured_records)} items from the page."
            output = {
                "cleaned_text": cleaned_text,
                "summary": summary,
                "page_type": "list_page",
                "source_url": source_url,
                "semantic_markdown": semantic_markdown,
                "files": normalized_files,
                "images": normalized_images,
                "tables": normalized_tables,
                "links": normalized_links,
                "items": structured_records,
            }

            return {
                "status": "success",
                "data": output,
                "error": None,
                "metadata": {
                    "agent": self.agent_name,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                },
            }

        page_type = classify_page_type(
            title=title_value,
            cleaned_text=cleaned_text,
            files=normalized_files,
            images=normalized_images,
            tables=normalized_tables,
            links=normalized_links,
        )
        summary = build_summary(
            title=title_value,
            cleaned_text=cleaned_text,
            page_type=page_type,
            files=normalized_files,
            images=normalized_images,
            tables=normalized_tables,
            links=normalized_links,
        )

        output = {
            "cleaned_text": cleaned_text,
            "summary": summary,
            "page_type": page_type,
            "source_url": source_url,
            "semantic_markdown": semantic_markdown,
            "files": normalized_files,
            "images": normalized_images,
            "tables": normalized_tables,
            "links": normalized_links,
            "items": [
                {
                    "type": "processed_page",
                    "source_url": source_url,
                    "title": title_value,
                    "content": cleaned_text,
                    "summary": summary,
                    "page_type": page_type,
                    "cleaned_text": cleaned_text,
                    "semantic_markdown": semantic_markdown,
                    "files": normalized_files,
                    "images": normalized_images,
                    "tables": normalized_tables,
                    "links": normalized_links,
                }
            ],
        }

        return {
            "status": "success",
            "data": output,
            "error": None,
            "metadata": {
                "agent": self.agent_name,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
        }

    def _resolve_extracted_payload(self, input_data: dict[str, Any]) -> Any:
        if "extracted" in input_data:
            return input_data["extracted"]
        if "data" in input_data and input_data.get("status") in {"success", "fail"}:
            return input_data
        if "pages" in input_data and isinstance(input_data["pages"], list) and input_data["pages"]:
            first_page = input_data["pages"][0]
            if isinstance(first_page, dict):
                return first_page
        return input_data

    def _resolve_source_url(self, input_data: dict[str, Any], extracted: dict[str, Any], data: dict[str, Any]) -> str:
        metadata = extracted.get("metadata", {}) if isinstance(extracted.get("metadata"), dict) else {}
        for candidate in (
            input_data.get("url"),
            metadata.get("source_url"),
            data.get("url"),
            data.get("final_url"),
        ):
            text = self._safe_text(candidate)
            if text:
                return text
        return ""

    def _failure_payload(self, error: str) -> dict[str, Any]:
        return {
            "status": "fail",
            "data": {
                "cleaned_text": "",
                "summary": "",
                "page_type": "",
                "source_url": "",
                "semantic_markdown": "",
                "files": [],
                "images": [],
                "tables": [],
                "links": [],
            },
            "error": error,
            "metadata": {
                "agent": self.agent_name,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
        }

    def _safe_text(self, value: Any) -> str:
        if value is None:
            return ""
        return str(value).strip()

    def _resolve_semantic_markdown(self, input_data: dict[str, Any]) -> str:
        markdown = input_data.get("semantic_markdown")
        if not isinstance(markdown, str):
            return ""
        cleaned = markdown.strip()
        if not cleaned:
            return ""
        return cleaned[:120_000]

    def _normalize_structured_records(self, records: Any, source_url: str) -> list[dict[str, Any]]:
        if not isinstance(records, list):
            return []

        normalized: list[dict[str, Any]] = []
        seen: set[tuple[str, str]] = set()

        for item in records:
            if not isinstance(item, dict):
                continue

            title = clean_text(str(item.get("title") or ""))
            link = urljoin(source_url, clean_text(str(item.get("link") or "")))
            price = clean_text(str(item.get("price") or ""))
            additional_fields = {
                str(key): clean_text(str(value))
                for key, value in item.items()
                if str(key) not in {"title", "price", "link"}
                and clean_text(str(value))
            }

            if not title and not link:
                continue

            key = (title.lower(), link.lower())
            if key in seen:
                continue
            seen.add(key)

            normalized.append({
                "type": "list_item",
                "source_url": source_url,
                "title": title,
                "price": price,
                "link": link,
                **additional_fields,
                "content": clean_text(
                    " ".join(
                        part
                        for part in [
                            title,
                            price,
                            link,
                            *additional_fields.values(),
                        ]
                        if part
                    )
                ),
            })

        return normalized

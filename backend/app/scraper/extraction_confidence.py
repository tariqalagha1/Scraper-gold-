from __future__ import annotations

from typing import Any


def _clamp(value: float) -> float:
    return round(max(0.0, min(1.0, value)), 2)


def text_confidence(value: str, *, preferred_source: str = "") -> float:
    if not value:
        return 0.0
    score = 0.45
    length = len(value.strip())
    if length >= 5:
        score += 0.15
    if length >= 20:
        score += 0.15
    if preferred_source in {"title", "heading", "paragraph"}:
        score += 0.15
    if any(char.isalpha() for char in value):
        score += 0.1
    return _clamp(score)


def collection_confidence(*, value: str, text_hint: str = "", source_tag: str = "") -> float:
    if not value:
        return 0.0
    score = 0.5
    if value.startswith(("http://", "https://")):
        score += 0.2
    if text_hint:
        score += 0.1
    if source_tag in {"a", "img", "video", "iframe", "source", "file"}:
        score += 0.15
    return _clamp(score)


def list_confidence(items: list[Any]) -> float:
    if not items:
        return 0.0
    score = 0.5
    if len(items) >= 2:
        score += 0.2
    if len(items) >= 5:
        score += 0.1
    if all(bool(item) for item in items):
        score += 0.1
    if any(isinstance(item, list) and item for item in items):
        score += 0.05
    return _clamp(score)

from __future__ import annotations

from urllib.parse import urlparse


PDF_EXTENSIONS = (".pdf",)
WORD_EXTENSIONS = (".doc", ".docx")
EXCEL_EXTENSIONS = (".xls", ".xlsx", ".csv")
IMAGE_EXTENSIONS = (".jpg", ".jpeg", ".png", ".gif", ".webp", ".svg", ".bmp", ".avif")
VIDEO_EXTENSIONS = (".mp4", ".webm", ".mov", ".m4v", ".avi", ".m3u8")
VIDEO_HOST_KEYWORDS = ("youtube", "youtu.be", "vimeo", "dailymotion", "wistia", "loom")


def normalize_href(href: str | None) -> str:
    if not href:
        return ""
    value = href.strip()
    if not value or value.startswith(("javascript:", "mailto:", "tel:", "#")):
        return ""
    return value


def classify_file_type(url: str) -> str | None:
    lowered = url.lower()
    if lowered.endswith(PDF_EXTENSIONS):
        return "pdf"
    if lowered.endswith(WORD_EXTENSIONS):
        return "word"
    if lowered.endswith(EXCEL_EXTENSIONS):
        return "excel"
    return None


def is_probable_image(url: str, tag_name: str | None = None) -> bool:
    lowered = url.lower()
    if tag_name == "img":
        return True
    return lowered.endswith(IMAGE_EXTENSIONS)


def is_probable_video(url: str, tag_name: str | None = None) -> bool:
    lowered = url.lower()
    parsed = urlparse(lowered)
    if tag_name in {"video", "source", "iframe"}:
        return True
    if lowered.endswith(VIDEO_EXTENSIONS):
        return True
    return any(keyword in parsed.netloc for keyword in VIDEO_HOST_KEYWORDS)

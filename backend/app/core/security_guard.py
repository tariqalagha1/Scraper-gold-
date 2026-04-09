from __future__ import annotations

import ipaddress
import re
from dataclasses import dataclass, field
from typing import Pattern
from urllib.parse import urlparse

from app.config import settings


_LOCAL_HOST_NAMES = {
    "localhost",
    "127.0.0.1",
    "::1",
    "0.0.0.0",
    "169.254.169.254",
    "metadata.google.internal",
    "metadata",
}
_LOCAL_SUFFIXES = (".local", ".internal", ".localhost", ".home.arpa")

_PROMPT_RISK_PATTERNS: tuple[tuple[str, Pattern[str], int], ...] = (
    (
        "instruction_override",
        re.compile(
            r"\b(ignore|bypass|override)\b.{0,30}\b(instructions?|rules|policy|guardrails|safety)\b",
            re.IGNORECASE | re.DOTALL,
        ),
        2,
    ),
    (
        "system_prompt_probe",
        re.compile(
            r"\b(system prompt|developer message|hidden instructions?)\b",
            re.IGNORECASE,
        ),
        2,
    ),
    (
        "secret_exfiltration",
        re.compile(
            r"\b(api[_ -]?key|token|secret|password|credential|environment variable|\.env)\b",
            re.IGNORECASE,
        ),
        2,
    ),
    (
        "tool_abuse",
        re.compile(
            r"\b(curl|wget|powershell|bash|python -c|os\.system|subprocess)\b",
            re.IGNORECASE,
        ),
        1,
    ),
    (
        "inline_script_payload",
        re.compile(r"(<script\b|javascript:|data:text/html)", re.IGNORECASE),
        1,
    ),
)


@dataclass
class PromptThreatReport:
    blocked: bool
    score: int
    matches: list[str] = field(default_factory=list)


def normalize_untrusted_text(value: str | None, *, max_chars: int | None = None) -> str:
    text = str(value or "").replace("\x00", "").strip()
    text = "".join(ch for ch in text if ch.isprintable() or ch in {"\n", "\t"})
    if max_chars and len(text) > max_chars:
        return text[:max_chars]
    return text


def inspect_prompt_for_injection(prompt: str | None) -> PromptThreatReport:
    if not settings.ENABLE_PROMPT_INJECTION_GUARD:
        return PromptThreatReport(blocked=False, score=0, matches=[])

    normalized = normalize_untrusted_text(prompt, max_chars=settings.SECURITY_PROMPT_MAX_CHARS).lower()
    if not normalized:
        return PromptThreatReport(blocked=False, score=0, matches=[])

    score = 0
    matches: list[str] = []
    for label, pattern, weight in _PROMPT_RISK_PATTERNS:
        if pattern.search(normalized):
            score += weight
            matches.append(label)

    return PromptThreatReport(
        blocked=score >= max(1, int(settings.SECURITY_PROMPT_BLOCK_THRESHOLD)),
        score=score,
        matches=matches,
    )


def normalize_and_validate_prompt(prompt: str | None) -> str | None:
    if prompt is None:
        return None
    normalized = normalize_untrusted_text(prompt, max_chars=settings.SECURITY_PROMPT_MAX_CHARS)
    if not normalized:
        return None
    report = inspect_prompt_for_injection(normalized)
    if report.blocked:
        matched = ", ".join(report.matches) or "unknown"
        raise ValueError(
            f"Prompt was blocked by the security guard ({matched}). "
            "Please remove instruction-override or secret-exfiltration text."
        )
    return normalized


def _is_loopback_host(hostname: str) -> bool:
    lowered = hostname.strip().lower().rstrip(".")
    if lowered in {"localhost", "127.0.0.1", "::1"}:
        return True
    try:
        ip = ipaddress.ip_address(lowered)
    except ValueError:
        return False
    return bool(ip.is_loopback)


def is_local_or_private_host(hostname: str) -> bool:
    lowered = hostname.strip().lower().rstrip(".")
    if not lowered:
        return True
    if lowered in _LOCAL_HOST_NAMES:
        return True
    if any(lowered.endswith(suffix) for suffix in _LOCAL_SUFFIXES):
        return True

    try:
        ip = ipaddress.ip_address(lowered)
    except ValueError:
        return False

    return bool(
        ip.is_private
        or ip.is_loopback
        or ip.is_link_local
        or ip.is_multicast
        or ip.is_reserved
        or ip.is_unspecified
    )


def is_host_allowed_for_outbound_requests(hostname: str) -> bool:
    lowered = hostname.strip().lower().rstrip(".")
    if not lowered:
        return False
    if not settings.BLOCK_PRIVATE_NETWORK_TARGETS:
        return True
    if not is_local_or_private_host(lowered):
        return True
    if settings.is_production:
        return False
    if settings.ALLOW_LOOPBACK_TARGETS_IN_NON_PRODUCTION and _is_loopback_host(lowered):
        return True
    return False


def validate_scrape_url(url: str | None, *, field_name: str = "url") -> str | None:
    normalized = normalize_untrusted_text(url, max_chars=2048)
    if not normalized:
        return f"Invalid {field_name}: value is required."

    try:
        parsed = urlparse(normalized)
    except Exception:
        return f"Invalid {field_name}: unable to parse URL."

    if parsed.scheme not in {"http", "https"}:
        return f"Invalid {field_name}: only http/https URLs are allowed."
    if not parsed.netloc:
        return f"Invalid {field_name}: missing host."
    if parsed.username or parsed.password:
        return f"Invalid {field_name}: embedded credentials are not allowed."

    hostname = (parsed.hostname or "").strip()
    if not hostname:
        return f"Invalid {field_name}: missing host."
    if not is_host_allowed_for_outbound_requests(hostname):
        return (
            f"Invalid {field_name}: private or local network targets are blocked by security policy."
        )

    return None

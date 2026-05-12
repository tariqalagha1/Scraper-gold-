"""Service layer for canonical integration scrape responses."""
from __future__ import annotations

from hashlib import sha256
import json
from typing import Any

from app.schemas.scrape import ScrapeQualityMetadata, ScrapeRequest, ScrapeResponse, ScrapeSource

CANONICAL_STATUS_VALUES = {"pending", "running", "partial_success", "completed", "failed", "cancelled", "timeout_recovered"}
PHONE_FIELDS = {"contact", "phone", "phone_number", "mobile", "telephone", "tel"}


def _normalize_field_name(value: str) -> str:
    return str(value or "").strip().lower()


def _normalize_value(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return str(value)
    return str(value).strip().lower()


def _normalize_phone_number(value: str) -> str | None:
    text = str(value or "").strip()
    if not text:
        return None

    has_leading_plus = text.startswith("+")
    digits = "".join(char for char in text if char.isdigit())
    if not digits:
        return None
    return f"+{digits}" if has_leading_plus else digits


def _normalize_field_value(field: str, value: Any) -> tuple[Any, bool]:
    if value is None:
        return None, False

    if not isinstance(value, str):
        return value, False

    original = value
    normalized = value.strip()
    changed = normalized != original

    if normalized == "":
        return None, True

    if "email" in field:
        lowered = normalized.lower()
        if lowered != normalized:
            changed = True
        normalized = lowered

    if field in PHONE_FIELDS or "phone" in field:
        normalized_phone = _normalize_phone_number(normalized)
        if normalized_phone is None:
            return None, True
        if normalized_phone != normalized:
            changed = True
        normalized = normalized_phone

    return normalized, changed


def normalize_records(records: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], int]:
    normalized_records: list[dict[str, Any]] = []
    normalized_fields_count = 0

    for raw_record in records:
        if not isinstance(raw_record, dict):
            continue

        normalized_record: dict[str, Any] = {}
        for key, value in raw_record.items():
            normalized_key = _normalize_field_name(str(key))
            if not normalized_key:
                continue

            normalized_value, changed = _normalize_field_value(normalized_key, value)
            if changed:
                normalized_fields_count += 1
            if normalized_value is not None:
                normalized_record[normalized_key] = normalized_value

        normalized_records.append(normalized_record)

    return normalized_records, normalized_fields_count


def _build_fallback_hash_key(normalized_record: dict[str, Any]) -> str:
    canonical_record = sorted((field, _normalize_value(value)) for field, value in normalized_record.items())
    encoded = json.dumps(canonical_record, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
    return sha256(encoded).hexdigest()


def _dedupe_fingerprint(normalized_record: dict[str, Any]) -> tuple[str, str, str]:
    name = _normalize_value(normalized_record.get("name"))
    email = _normalize_value(normalized_record.get("email"))
    contact = _normalize_value(normalized_record.get("contact"))

    if name and email:
        return ("name_email", name, email)
    if name and contact:
        return ("name_contact", name, contact)
    return ("record_hash", _build_fallback_hash_key(normalized_record), "")


def deduplicate_records(records: list[dict[str, Any]], fields: list[str]) -> tuple[list[dict[str, Any]], int]:
    if not records:
        return [], 0

    _ = fields
    deduped: list[dict[str, Any]] = []
    seen: set[tuple[str, str, str]] = set()
    duplicates_removed = 0

    for raw_record in records:
        if not isinstance(raw_record, dict):
            continue

        normalized_record = {
            _normalize_field_name(str(key)): value
            for key, value in raw_record.items()
            if _normalize_field_name(str(key))
        }
        fingerprint = _dedupe_fingerprint(normalized_record)

        if fingerprint in seen:
            duplicates_removed += 1
            continue
        seen.add(fingerprint)
        deduped.append(normalized_record)

    return deduped, max(0, duplicates_removed)


def filter_by_schema(records: list[dict[str, Any]], required_fields: list[str], minimum_completeness: int, fields: list[str]) -> list[dict[str, Any]]:
    filtered: list[dict[str, Any]] = []
    normalized_required = set(_normalize_field_name(f) for f in required_fields if _normalize_field_name(f))
    normalized_fields = set(_normalize_field_name(f) for f in fields if _normalize_field_name(f))
    
    for record in records:
        # Check required fields
        has_all_required = True
        for req_field in normalized_required:
            val = record.get(req_field)
            if val is None or _normalize_value(val) == "":
                has_all_required = False
                break
        
        if not has_all_required:
            continue
            
        # Check completeness
        if minimum_completeness > 0 and normalized_fields:
            populated = sum(1 for f in normalized_fields if record.get(f) is not None and _normalize_value(record.get(f)) != "")
            completeness = (populated / len(normalized_fields)) * 100
            if completeness < minimum_completeness:
                continue
                
        # Only keep schema fields
        schema_record = {}
        for k, v in record.items():
            if k in normalized_fields or k in {"confidence", "source_url"}:
                schema_record[k] = v
        filtered.append(schema_record)
        
    return filtered


def calculate_coverage(records: list[dict[str, Any]], fields: list[str]) -> float:
    normalized_fields = [_normalize_field_name(field) for field in fields if _normalize_field_name(field)]
    if not records or not normalized_fields:
        return 0.0

    populated_slots = 0
    total_slots = len(records) * len(normalized_fields)
    if total_slots <= 0:
        return 0.0

    for record in records:
        if not isinstance(record, dict):
            continue
        normalized_record = {_normalize_field_name(str(key)): value for key, value in record.items()}
        for field in normalized_fields:
            if _normalize_value(normalized_record.get(field)):
                populated_slots += 1

    return min(1.0, populated_slots / total_slots)


def summarize_missing_fields(records: list[dict[str, Any]], fields: list[str]) -> dict[str, int]:
    normalized_fields = [_normalize_field_name(field) for field in fields if _normalize_field_name(field)]
    missing_counts: dict[str, int] = {field: 0 for field in normalized_fields}

    if not records or not normalized_fields:
        return missing_counts

    for record in records:
        if not isinstance(record, dict):
            for field in missing_counts:
                missing_counts[field] += 1
            continue

        normalized_record = {_normalize_field_name(str(key)): value for key, value in record.items()}
        for field in normalized_fields:
            if not _normalize_value(normalized_record.get(field)):
                missing_counts[field] += 1

    return missing_counts


def calculate_confidence(
    *,
    coverage: float,
    total_records: int,
    duplicates_removed: int,
    missing_fields: dict[str, int],
    errors_count: int,
) -> float:
    _ = missing_fields
    if total_records <= 0:
        return 0.0

    duplicate_ratio = max(0.0, min(1.0, duplicates_removed / total_records))
    error_ratio = max(0.0, min(1.0, errors_count / total_records))
    score = coverage * duplicate_ratio * error_ratio
    return max(0.0, min(1.0, score))


def normalize_status(raw_status: str | None, *, has_errors: bool = False, total_records: int = 0) -> str:
    normalized = _normalize_value(raw_status)
    if not normalized:
        return "failed" if total_records <= 0 else "completed"

    if normalized in CANONICAL_STATUS_VALUES:
        if normalized in {"failed", "cancelled"}:
            return "failed"
        if normalized == "completed" and has_errors:
            return "partial"
        if normalized == "completed" and total_records <= 0:
            return "failed"
        if normalized in {"pending", "running", "partial_success", "timeout_recovered"}:
            return "partial"
        return normalized

    if total_records <= 0:
        return "failed"

    if normalized in {"failed", "error", "cancelled", "canceled", "timeout"}:
        return "failed"
    if has_errors:
        return "partial"
    if normalized in {"partial", "completed_with_errors", "queued", "pending", "running", "in_progress", "processing"}:
        return "partial"
    if normalized in {"completed", "complete", "done", "success", "ok"}:
        return "completed"
    return "completed"


def _extract_source_name(record: dict[str, Any]) -> str:
    for key in ("source", "source_name", "source_url", "domain", "url"):
        name = _normalize_value(record.get(key))
        if name:
            return name
    return ""


def build_sources_breakdown(records: list[dict[str, Any]], raw_sources: list[Any] | None) -> list[ScrapeSource]:
    source_counts: dict[str, int] = {}
    for record in records:
        source_name = _extract_source_name(record)
        if source_name:
            source_counts[source_name] = source_counts.get(source_name, 0) + 1

    for source in raw_sources or []:
        if isinstance(source, dict):
            name = _normalize_value(source.get("name"))
            try:
                fallback_count = max(0, int(source.get("count", 0)))
            except (TypeError, ValueError):
                fallback_count = 0
        elif hasattr(source, "name"):
            name = _normalize_value(getattr(source, "name"))
            fallback_count = 0
        else:
            name = _normalize_value(source)
            fallback_count = 0
        if name and name not in source_counts:
            source_counts[name] = fallback_count

    return [ScrapeSource(name=name, count=count) for name, count in sorted(source_counts.items())]


def normalize_errors(raw_errors: Any) -> list[str]:
    if raw_errors is None:
        return []

    if isinstance(raw_errors, list):
        candidates = raw_errors
    else:
        candidates = [raw_errors]

    errors: list[str] = []
    for candidate in candidates:
        if candidate is None:
            continue
        if isinstance(candidate, str):
            text = candidate.strip()
        elif isinstance(candidate, dict):
            text = ""
            for key in ("message", "error", "detail", "reason"):
                value = candidate.get(key)
                if isinstance(value, str) and value.strip():
                    text = value.strip()
                    break
            if not text:
                text = json.dumps(candidate, ensure_ascii=True, sort_keys=True)
        else:
            text = str(candidate).strip()

        if text:
            errors.append(text)
    return errors


def resolve_request_id(request: ScrapeRequest) -> str:
    if request.request_id:
        return request.request_id

    stable_payload = {
        "query": request.query,
        "location": request.location,
        "limit": request.limit,
        "fields": sorted({_normalize_field_name(field) for field in request.fields if _normalize_field_name(field)}),
        "source_type": request.source_type or "",
    }
    digest = sha256(json.dumps(stable_payload, sort_keys=True).encode("utf-8")).hexdigest()[:16]
    return f"req_{digest}"


def build_quality_metadata(
    *,
    records: list[dict[str, Any]],
    fields: list[str],
    duplicates_removed: int,
    errors_count: int,
    normalized_fields_count: int,
) -> ScrapeQualityMetadata:
    coverage = calculate_coverage(records, fields)
    missing_fields = summarize_missing_fields(records, fields)
    confidence = calculate_confidence(
        coverage=coverage,
        total_records=len(records),
        duplicates_removed=duplicates_removed,
        missing_fields=missing_fields,
        errors_count=errors_count,
    )
    return ScrapeQualityMetadata(
        duplicates_removed=max(0, int(duplicates_removed)),
        coverage=coverage,
        confidence=confidence,
        missing_fields=missing_fields,
        normalized_fields=max(0, int(normalized_fields_count)),
    )


def execute_scrape_contract(request: ScrapeRequest) -> ScrapeResponse:
    """Return a deterministic response contract from placeholder scrape output."""
    raw_records: list[dict[str, Any]] = [] # This would be replaced with actual extraction logic
    normalized_records, normalized_fields_count = normalize_records(raw_records)
    
    # Apply deterministic validation
    filtered_records = filter_by_schema(
        records=normalized_records, 
        required_fields=request.required_fields, 
        minimum_completeness=request.minimum_completeness, 
        fields=request.fields
    )
    
    deduped_records, duplicates_removed = deduplicate_records(filtered_records, request.fields)
    selected_records = deduped_records[: request.limit]
    quality = build_quality_metadata(
        records=selected_records,
        fields=request.fields,
        duplicates_removed=duplicates_removed,
        errors_count=0,
        normalized_fields_count=normalized_fields_count,
    )

    return ScrapeResponse(
        request_id=resolve_request_id(request),
        status=normalize_status("completed", has_errors=False, total_records=len(selected_records)),
        execution_time=0.0,
        total=len(selected_records),
        data=selected_records,
        sources=build_sources_breakdown(selected_records, [request.source_type] if request.source_type else []),
        errors=[],
        quality=quality,
    )

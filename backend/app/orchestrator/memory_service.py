from __future__ import annotations

import os
from datetime import datetime, timezone
from functools import lru_cache
from typing import Any

from app.config import settings
from app.core.logging import get_logger


logger = get_logger("app.orchestrator.memory_service")
TABLE_NAME = "domain_memory"

# NOTE:
# Supabase calls are network-bound and must never block core execution.
# All operations must fail safely without affecting scraping flow.


def log_memory_backend_startup_status() -> None:
    """Log memory backend readiness during app startup without raising."""
    try:
        client = _get_supabase_client()
        if client is None:
            logger.error(
                "Supabase memory backend unavailable at startup. Persistent memory is disabled."
            )
            return
        logger.info("Supabase memory backend ready.")
    except Exception as exc:
        logger.error(
            "Supabase memory backend startup check failed.",
            error=str(exc),
        )


@lru_cache(maxsize=1)
def _get_supabase_client() -> Any | None:
    """Build a cached Supabase client lazily so failures stay isolated."""
    try:
        from supabase import create_client
    except Exception as exc:
        logger.error("Supabase client import failed.", error=str(exc))
        return None

    supabase_url = (
        str(getattr(settings, "SUPABASE_URL", "") or os.getenv("SUPABASE_URL", ""))
        .strip()
    )
    service_role_key = (
        str(
            getattr(settings, "SUPABASE_SERVICE_ROLE_KEY", "")
            or os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
        )
        .strip()
    )

    if not supabase_url or not service_role_key:
        logger.warning(
            "Supabase memory service is not configured.",
            has_supabase_url=bool(supabase_url),
            has_service_role_key=bool(service_role_key),
        )
        return None

    try:
        return create_client(supabase_url, service_role_key)
    except Exception as exc:
        logger.error("Supabase client initialization failed.", error=str(exc))
        return None


def get_domain_memory(domain: str, page_type: str | None = None) -> dict[str, Any] | None:
    """Return the best active memory row for a domain and optional page type."""
    try:
        normalized_domain = str(domain).strip().lower()
        normalized_domain = normalized_domain.replace("www.", "")
        normalized_domain = normalized_domain.split(":")[0]
        if not normalized_domain:
            logger.warning("Domain memory lookup skipped because domain is empty.")
            return None

        client = _get_supabase_client()
        if client is None:
            return None

        query = (
            client.table(TABLE_NAME)
            .select("*")
            .eq("domain", normalized_domain)
            .eq("is_active", True)
        )
        if page_type:
            query = query.eq("page_type", str(page_type).strip().lower())

        response = (
            query
            .order("success_rate", desc=True)
            .order("sample_count", desc=True)
            .order("last_updated", desc=True)
            .limit(1)
            .execute()
        )

        rows = getattr(response, "data", None) or []
        if not rows:
            logger.info("Domain memory miss.", domain=normalized_domain, page_type=page_type)
            return None

        memory = rows[0]
        try:
            client.table(TABLE_NAME).update({
                "last_used_at": datetime.now(timezone.utc).isoformat()
            }).eq("id", memory["id"]).execute()
        except Exception:
            pass

        logger.info(
            "Domain memory hit.",
            domain=normalized_domain,
            page_type=page_type,
            memory_id=memory.get("id"),
        )
        return memory
    except Exception as exc:
        logger.error(
            "Domain memory lookup failed.",
            domain=domain,
            page_type=page_type,
            error=str(exc),
        )
        return None


def is_memory_usable(memory: dict[str, Any] | None) -> bool:
    if not isinstance(memory, dict):
        return False

    selectors = memory.get("selectors")
    success_rate = memory.get("success_rate", 0)
    is_active = memory.get("is_active", False)

    try:
        return (
            isinstance(selectors, dict)
            and bool(is_active)
            and float(success_rate) >= 0.5
        )
    except Exception:
        return False


def update_domain_memory_stats(existing: dict[str, Any]) -> dict[str, Any]:
    old_count = int(existing.get("sample_count", 0) or 0)
    old_rate = float(existing.get("success_rate", 0.0) or 0.0)
    new_count = old_count + 1
    new_rate = ((old_rate * old_count) + 1.0) / new_count

    timestamp = datetime.now(timezone.utc).isoformat()
    return {
        "sample_count": new_count,
        "success_rate": max(0.0, min(1.0, new_rate)),
        "last_updated": timestamp,
        "updated_at": timestamp,
    }


def save_domain_memory(domain: str, decision: dict[str, Any], validation: dict[str, Any]) -> None:
    """Persist successful selector memory for later domain reuse."""
    try:
        if validation.get("status") != "pass":
            return

        normalized_domain = str(domain).strip().lower()
        normalized_domain = normalized_domain.replace("www.", "")
        normalized_domain = normalized_domain.split(":")[0]
        if not normalized_domain:
            logger.warning("Domain memory save skipped because domain is empty.")
            return

        page_type = str(decision.get("page_type") or "unknown").strip().lower()
        selectors = decision.get("selectors")
        source = str(decision.get("source") or "generated").strip().lower()

        if not isinstance(selectors, dict) or not selectors.get("container"):
            logger.warning(
                "Skipping memory save due to invalid selectors.",
                domain=normalized_domain,
                page_type=page_type,
            )
            return

        client = _get_supabase_client()
        if client is None:
            return

        existing = get_domain_memory(normalized_domain, page_type)
        timestamp = datetime.now(timezone.utc).isoformat()

        if existing:
            existing_rate = float(existing.get("success_rate", 0.0))
            existing_count = int(existing.get("sample_count", 0))

            if existing_rate > 0.8 and existing_count > 5:
                logger.info(
                    "Skipping overwrite of strong memory.",
                    domain=normalized_domain,
                    page_type=page_type,
                    success_rate=existing_rate,
                )
                return

            updated_fields = update_domain_memory_stats(existing)
            updated_fields.update(
                {
                    "selectors": selectors,
                    "source": source,
                    "debug_metadata": {
                        "last_validation_status": "pass",
                        "last_confidence": validation.get("confidence", 0),
                    },
                }
            )

            (
                client.table(TABLE_NAME)
                .update(updated_fields)
                .eq("id", existing["id"])
                .execute()
            )
            logger.info(
                "Domain memory updated.",
                domain=normalized_domain,
                page_type=page_type,
                memory_id=existing.get("id"),
                sample_count=updated_fields.get("sample_count"),
                success_rate=updated_fields.get("success_rate"),
            )
            return

        payload = {
            "domain": normalized_domain,
            "page_type": page_type,
            "selectors": selectors,
            "success_rate": 1.0,
            "sample_count": 1,
            "source": source,
            "is_active": True,
            "last_updated": timestamp,
            "created_at": timestamp,
            "updated_at": timestamp,
            "debug_metadata": {
                "last_validation_status": "pass",
                "last_confidence": validation.get("confidence", 0),
            },
        }

        client.table(TABLE_NAME).insert(payload).execute()
        logger.info(
            "Domain memory saved.",
            domain=normalized_domain,
            page_type=page_type,
            success_rate=1.0,
            sample_count=1,
        )
    except Exception as exc:
        logger.error(
            "Domain memory save failed.",
            domain=domain,
            page_type=decision.get("page_type"),
            error=str(exc),
        )

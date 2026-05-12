from __future__ import annotations

from collections.abc import Iterable
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.logging import get_logger
from app.core.secrets import build_masked_secret, decrypt_secret, encrypt_secret
from app.models.system_secret import SystemSecret
from app.models.user import User
from app.schemas.system_secret import SystemSecretItem


logger = get_logger("app.services.system_secrets")

SUPPORTED_SYSTEM_SECRET_KEYS = (
    "SECRET_KEY",
    "API_KEY",
    "SCRAPER_API_KEY",
    "OPENAI_API_KEY",
)
_SUPPORTED_SET = set(SUPPORTED_SYSTEM_SECRET_KEYS)
_BASE_SYSTEM_SECRET_VALUES = {
    key: str(getattr(settings, key, "") or "").strip()
    for key in SUPPORTED_SYSTEM_SECRET_KEYS
}


def normalize_system_secret_name(name: str) -> str:
    return str(name or "").strip().upper()


def ensure_supported_system_secret(name: str) -> str:
    normalized = normalize_system_secret_name(name)
    if normalized not in _SUPPORTED_SET:
        raise ValueError(f"Unsupported system secret: {normalized}")
    return normalized


def _admin_emails() -> set[str]:
    return {
        str(item).strip().lower()
        for item in (settings.SYSTEM_KEYS_ADMIN_EMAILS or [])
        if str(item).strip()
    }


def can_manage_system_secrets(user: User) -> bool:
    admins = _admin_emails()
    if not admins:
        # Backward-compatible default for single-tenant/internal setups.
        return True
    return str(user.email or "").strip().lower() in admins


def is_system_secret_configured_in_env(name: str) -> bool:
    normalized = ensure_supported_system_secret(name)
    value = str(getattr(settings, normalized, "") or "").strip()
    return bool(value)


def _effective_secret_source(name: str, db_secret: SystemSecret | None) -> str:
    if db_secret and db_secret.is_active:
        return "database"
    if is_system_secret_configured_in_env(name):
        return "env"
    return "unset"


def _effective_secret_value_from_record(name: str, db_secret: SystemSecret | None) -> str:
    if db_secret and db_secret.is_active:
        try:
            return decrypt_secret(db_secret.encrypted_value, allow_plaintext_fallback=False)
        except ValueError:
            logger.warning("Stored system secret could not be decrypted.", key=name)
            return ""
    return str(getattr(settings, name, "") or "").strip()


def apply_runtime_system_overrides(values: dict[str, str]) -> None:
    for key, value in values.items():
        normalized = normalize_system_secret_name(key)
        if normalized in _SUPPORTED_SET:
            setattr(settings, normalized, str(value or "").strip())


async def fetch_system_secret_records(db: AsyncSession) -> dict[str, SystemSecret]:
    result = await db.execute(
        select(SystemSecret).where(SystemSecret.is_active.is_(True))
    )
    records = {}
    for item in result.scalars().all():
        name = normalize_system_secret_name(item.name)
        if name in _SUPPORTED_SET:
            records[name] = item
    return records


async def get_effective_system_secret(db: AsyncSession, name: str) -> str:
    normalized = ensure_supported_system_secret(name)
    record = await db.scalar(
        select(SystemSecret).where(
            SystemSecret.name == normalized,
            SystemSecret.is_active.is_(True),
        )
    )
    return _effective_secret_value_from_record(normalized, record)


async def get_effective_system_secrets(db: AsyncSession) -> dict[str, str]:
    records = await fetch_system_secret_records(db)
    values = {
        key: _effective_secret_value_from_record(key, records.get(key))
        for key in SUPPORTED_SYSTEM_SECRET_KEYS
    }
    apply_runtime_system_overrides(values)
    return values


async def list_system_secret_items(db: AsyncSession) -> list[SystemSecretItem]:
    records = await fetch_system_secret_records(db)

    updated_by_ids = {
        item.updated_by_user_id
        for item in records.values()
        if item.updated_by_user_id is not None
    }
    email_by_id: dict[UUID, str] = {}
    if updated_by_ids:
        user_rows = await db.execute(
            select(User.id, User.email).where(User.id.in_(updated_by_ids))
        )
        email_by_id = {row[0]: row[1] for row in user_rows.all()}

    items: list[SystemSecretItem] = []
    for key in SUPPORTED_SYSTEM_SECRET_KEYS:
        record = records.get(key)
        source = _effective_secret_source(key, record)
        configured = source != "unset"
        items.append(
            SystemSecretItem(
                name=key,
                configured=configured,
                source=source,  # type: ignore[arg-type]
                key_mask=record.key_mask if record else (build_masked_secret(getattr(settings, key, "")) if configured else None),
                updated_at=record.updated_at if record else None,
                updated_by_email=(email_by_id.get(record.updated_by_user_id) if record and record.updated_by_user_id else None),
            )
        )
    return items


async def upsert_system_secret(
    db: AsyncSession,
    *,
    name: str,
    value: str,
    updated_by_user_id: UUID | None,
) -> SystemSecret:
    normalized = ensure_supported_system_secret(name)
    raw_value = str(value or "").strip()
    if not raw_value:
        raise ValueError("System secret value cannot be empty.")

    encrypted = encrypt_secret(raw_value)
    mask = build_masked_secret(raw_value)
    record = await db.scalar(select(SystemSecret).where(SystemSecret.name == normalized))
    if record is None:
        record = SystemSecret(
            name=normalized,
            encrypted_value=encrypted,
            key_mask=mask,
            is_active=True,
            updated_by_user_id=updated_by_user_id,
        )
        db.add(record)
    else:
        record.encrypted_value = encrypted
        record.key_mask = mask
        record.is_active = True
        record.updated_by_user_id = updated_by_user_id

    await db.commit()
    await db.refresh(record)
    apply_runtime_system_overrides({normalized: raw_value})
    return record


async def delete_system_secret(db: AsyncSession, *, name: str) -> bool:
    normalized = ensure_supported_system_secret(name)
    record = await db.scalar(select(SystemSecret).where(SystemSecret.name == normalized))
    if record is None:
        return False
    await db.delete(record)
    await db.commit()
    setattr(settings, normalized, _BASE_SYSTEM_SECRET_VALUES.get(normalized, ""))
    return True


def coerce_system_secret_subset(values: dict[str, Any], names: Iterable[str]) -> dict[str, str]:
    subset: dict[str, str] = {}
    for name in names:
        normalized = normalize_system_secret_name(name)
        if normalized in _SUPPORTED_SET:
            subset[normalized] = str(values.get(normalized, "") or "").strip()
    return subset

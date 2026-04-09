from __future__ import annotations

from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.core.secrets import build_masked_secret, decrypt_secret, encrypt_secret
from app.models.user_api_key import UserApiKey
from app.schemas.credential import CredentialResponse


logger = get_logger("app.services.user_credentials")


SUPPORTED_PROVIDERS = {
    "openai",
    "anthropic",
    "gemini",
    "serper",
}


def normalize_provider(provider: str) -> str:
    return str(provider or "").strip().lower()


def encrypt_api_key(raw_key: str) -> str:
    return encrypt_secret(raw_key)


def decrypt_api_key(encrypted_key: str) -> str:
    return decrypt_secret(encrypted_key, allow_plaintext_fallback=False)


def build_masked_key(raw_key: str) -> str:
    return build_masked_secret(raw_key)


def serialize_credential(credential: UserApiKey) -> CredentialResponse:
    return CredentialResponse(
        id=credential.id,
        provider=credential.provider,
        key_mask=credential.key_mask,
        is_active=credential.is_active,
        created_at=credential.created_at,
        updated_at=credential.updated_at,
    )


async def upsert_user_credential(
    db: AsyncSession,
    *,
    user_id: UUID,
    provider: str,
    api_key: str,
) -> UserApiKey:
    normalized_provider = normalize_provider(provider)
    if normalized_provider not in SUPPORTED_PROVIDERS:
        raise ValueError(f"Unsupported provider: {normalized_provider}")

    encrypted_key = encrypt_api_key(api_key)
    key_mask = build_masked_key(api_key)

    existing = await db.scalar(
        select(UserApiKey).where(
            UserApiKey.user_id == user_id,
            UserApiKey.provider == normalized_provider,
        )
    )

    if existing:
        existing.encrypted_key = encrypted_key
        existing.key_mask = key_mask
        existing.is_active = True
        await db.commit()
        await db.refresh(existing)
        logger.info("Provider credential updated.", user_id=str(user_id), provider=normalized_provider)
        return existing

    credential = UserApiKey(
        user_id=user_id,
        provider=normalized_provider,
        encrypted_key=encrypted_key,
        key_mask=key_mask,
        is_active=True,
    )
    db.add(credential)
    await db.commit()
    await db.refresh(credential)
    logger.info("Provider credential created.", user_id=str(user_id), provider=normalized_provider)
    return credential


async def list_user_credentials(
    db: AsyncSession,
    *,
    user_id: UUID,
    skip: int = 0,
    limit: int = 50,
) -> tuple[list[UserApiKey], int]:
    total = (
        await db.execute(select(func.count(UserApiKey.id)).where(UserApiKey.user_id == user_id))
    ).scalar() or 0
    result = await db.execute(
        select(UserApiKey)
        .where(UserApiKey.user_id == user_id)
        .order_by(UserApiKey.provider.asc())
        .offset(skip)
        .limit(limit)
    )
    return list(result.scalars().all()), int(total)


async def delete_user_credential(
    db: AsyncSession,
    *,
    user_id: UUID,
    provider: str,
) -> bool:
    normalized_provider = normalize_provider(provider)
    credential = await db.scalar(
        select(UserApiKey).where(
            UserApiKey.user_id == user_id,
            UserApiKey.provider == normalized_provider,
        )
    )
    if credential is None:
        return False
    await db.delete(credential)
    await db.commit()
    logger.info("Provider credential deleted.", user_id=str(user_id), provider=normalized_provider)
    return True


async def get_user_provider_credentials(
    db: AsyncSession,
    *,
    user_id: UUID,
) -> dict[str, str]:
    result = await db.execute(
        select(UserApiKey).where(
            UserApiKey.user_id == user_id,
            UserApiKey.is_active.is_(True),
        )
    )
    credentials: dict[str, str] = {}
    for item in result.scalars().all():
        try:
            credentials[item.provider] = decrypt_api_key(item.encrypted_key)
        except ValueError:
            logger.warning(
                "Skipping undecryptable provider credential.",
                user_id=str(user_id),
                provider=item.provider,
            )
    return credentials

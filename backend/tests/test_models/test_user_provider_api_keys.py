import pytest
from sqlalchemy import Text, cast, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.secrets import is_encrypted_secret
from app.models.user import User
from app.models.user_api_key import UserApiKey
from app.services.user_credentials import upsert_user_credential


pytestmark = pytest.mark.asyncio


async def test_provider_api_key_is_encrypted_at_rest(db_session: AsyncSession):
    user = User(email="provider-key-encryption@example.com", hashed_password="hashed", is_active=True)
    db_session.add(user)
    await db_session.flush()

    raw_key = "sk-live-provider-raw-key-123456789"
    await upsert_user_credential(
        db=db_session,
        user_id=user.id,
        provider="openai",
        api_key=raw_key,
    )

    stored_encrypted = (
        await db_session.execute(
            select(cast(UserApiKey.__table__.c.encrypted_key, Text)).where(
                UserApiKey.user_id == user.id,
                UserApiKey.provider == "openai",
            )
        )
    ).scalar_one()

    assert stored_encrypted != raw_key
    assert is_encrypted_secret(stored_encrypted)

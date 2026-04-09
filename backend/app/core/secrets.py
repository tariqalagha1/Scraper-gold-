from __future__ import annotations

from typing import Any

from cryptography.fernet import Fernet, InvalidToken
from sqlalchemy.types import Text, TypeDecorator

from app.config import settings


def _get_cipher() -> Fernet:
    return Fernet(settings.resolved_provider_api_key_encryption_key.encode("utf-8"))


def encrypt_secret(raw_value: str) -> str:
    value = str(raw_value or "").strip()
    if not value:
        return ""
    return _get_cipher().encrypt(value.encode("utf-8")).decode("utf-8")


def decrypt_secret(encrypted_value: str, *, allow_plaintext_fallback: bool = False) -> str:
    value = str(encrypted_value or "")
    if not value:
        return ""
    try:
        return _get_cipher().decrypt(value.encode("utf-8")).decode("utf-8")
    except InvalidToken as exc:
        if allow_plaintext_fallback:
            return value
        raise ValueError("Credential could not be decrypted.") from exc


def is_encrypted_secret(value: str) -> bool:
    try:
        decrypt_secret(value, allow_plaintext_fallback=False)
    except ValueError:
        return False
    return True


def build_masked_secret(raw_value: str) -> str:
    value = str(raw_value or "").strip()
    if len(value) <= 8:
        return "Stored securely"
    return f"{value[:4]}...{value[-4:]}"


class EncryptedText(TypeDecorator[str]):
    """Persist decrypted strings while storing encrypted values in the database."""

    impl = Text
    cache_ok = True

    def process_bind_param(self, value: Any, dialect: Any) -> str | None:
        if value is None:
            return None
        encrypted = encrypt_secret(str(value))
        return encrypted or None

    def process_result_value(self, value: Any, dialect: Any) -> str | None:
        if value is None:
            return None
        return decrypt_secret(str(value), allow_plaintext_fallback=True)

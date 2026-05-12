from jose import jwt
import pytest

from app.config import settings
from app.core.exceptions import AuthenticationError
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_access_token,
    get_token_payload,
)


def test_decode_access_token_accepts_access_tokens():
    token = create_access_token({"sub": "user-123", "email": "user@example.com"})

    payload = decode_access_token(token)

    assert payload["sub"] == "user-123"
    assert payload["type"] == "access"
    assert payload.get("jti")


def test_decode_access_token_rejects_refresh_tokens():
    token = create_refresh_token({"sub": "user-123"})

    with pytest.raises(AuthenticationError):
        decode_access_token(token)


def test_decode_access_token_rejects_missing_subject():
    token = jwt.encode({"type": "access"}, settings.SECRET_KEY, algorithm=settings.ALGORITHM)

    with pytest.raises(AuthenticationError):
        decode_access_token(token)


def test_get_token_payload_allows_refresh_token_introspection():
    token = create_refresh_token({"sub": "user-123"})

    payload = get_token_payload(token)

    assert payload is not None
    assert payload["type"] == "refresh"

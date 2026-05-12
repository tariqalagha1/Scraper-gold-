"""Shared API dependencies.

Provides common dependencies for route handlers including database sessions,
authentication, and current user retrieval.
"""
import secrets
from typing import AsyncGenerator
from uuid import UUID

from fastapi import Depends, Header, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.exceptions import AuthenticationError
from app.core.security import decode_access_token
from app.core.logging import get_logger
from app.db.session import get_db_session
from app.models.api_key import ApiKey
from app.models.user import User
from app.services.system_secrets import get_effective_system_secret
from app.services.saas import hash_api_key
from app.storage.manager import StorageManager


# OAuth2 scheme for token extraction
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login", auto_error=False)
logger = get_logger("app.api.deps")


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency to get database session.
    
    Yields:
        AsyncSession: Database session for the current request.
    """
    async for session in get_db_session():
        yield session


async def get_current_user(
    token: str | None = Depends(oauth2_scheme),
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
    configured_header_key: str | None = Header(default=None, alias=settings.API_KEY_HEADER_NAME),
    db: AsyncSession = Depends(get_db),
) -> User:
    """Dependency to get the current authenticated user from JWT token.
    
    Args:
        token: JWT token from Authorization header.
        db: Database session.
        
    Returns:
        User: The authenticated user.
        
    Raises:
        HTTPException: If token is invalid or user not found.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    user_id: UUID | None = None
    provided_api_key = (x_api_key or configured_header_key or "").strip() or None

    if token:
        try:
            payload = decode_access_token(token)
            user_id_str: str | None = payload.get("sub")
            if user_id_str is None:
                raise credentials_exception

            try:
                user_id = UUID(user_id_str)
            except ValueError:
                raise credentials_exception
        except AuthenticationError:
            raise credentials_exception
    elif provided_api_key:
        expected_api_key = (await get_effective_system_secret(db, "API_KEY")).strip()
        if expected_api_key and secrets.compare_digest(provided_api_key, expected_api_key):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Global API key cannot be used as a user credential",
            )

        stmt = select(ApiKey).where(
            ApiKey.key == hash_api_key(provided_api_key),
            ApiKey.is_active.is_(True),
        )
        result = await db.execute(stmt)
        api_key_record = result.scalar_one_or_none()
        if api_key_record is None:
            raise credentials_exception
        user_id = api_key_record.user_id
    else:
        raise credentials_exception
    
    # Fetch user from database
    stmt = select(User).where(User.id == user_id)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()
    
    if user is None:
        raise credentials_exception
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Inactive user account",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return user


async def get_current_active_user(
    current_user: User = Depends(get_current_user),
) -> User:
    """Dependency to ensure the current user is active.
    
    Args:
        current_user: The current authenticated user.
        
    Returns:
        User: The active user.
        
    Raises:
        HTTPException: If user is not active.
    """
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Inactive user account",
        )
    return current_user


def get_storage() -> StorageManager:
    """Dependency to get storage manager instance.
    
    Returns:
        StorageManager: Storage manager for file operations.
    """
    return StorageManager()


async def verify_api_key(
    token: str | None = Depends(oauth2_scheme),
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
    configured_header_key: str | None = Header(default=None, alias=settings.API_KEY_HEADER_NAME),
    db: AsyncSession = Depends(get_db),
) -> str | None:
    expected_api_key = (await get_effective_system_secret(db, "API_KEY")).strip()
    provided_api_key = (x_api_key or configured_header_key or "").strip() or None

    token_user_id: UUID | None = None
    if token:
        try:
            payload = decode_access_token(token)
            token_subject = str(payload.get("sub") or "").strip()
            if token_subject:
                token_user_id = UUID(token_subject)
        except (AuthenticationError, ValueError):
            token_user_id = None

    if not provided_api_key:
        logger.warning(
            "API key missing on protected endpoint.",
            auth_source="missing_api_key",
            has_jwt=bool(token_user_id),
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing API key",
        )

    if provided_api_key and expected_api_key and secrets.compare_digest(provided_api_key, expected_api_key):
        logger.info(
            "Global API key accepted.",
            auth_source="global_api_key",
            user_id=str(token_user_id) if token_user_id else None,
        )
        return provided_api_key

    stmt = select(ApiKey).where(
        ApiKey.key == hash_api_key(provided_api_key),
        ApiKey.is_active.is_(True),
    )
    result = await db.execute(stmt)
    api_key_record = result.scalar_one_or_none()
    if api_key_record is None:
        logger.warning("Invalid API key rejected.", auth_source="invalid_api_key")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid API key",
        )

    if token_user_id and api_key_record.user_id != token_user_id:
        logger.warning(
            "API key does not match authenticated user.",
            auth_source="api_key_user_mismatch",
            token_user_id=str(token_user_id),
            api_key_user_id=str(api_key_record.user_id),
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid API key",
        )

    logger.info(
        "User API key accepted.",
        auth_source="user_api_key",
        user_id=str(api_key_record.user_id),
    )
    return provided_api_key


__all__ = [
    "get_db",
    "get_current_user",
    "get_current_active_user",
    "get_storage",
    "verify_api_key",
]

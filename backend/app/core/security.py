"""Security utilities for JWT authentication and password hashing.

Provides secure password hashing using bcrypt and JWT token
creation/validation using python-jose.
"""
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.config import settings
from app.core.exceptions import AuthenticationError

# Prefer pbkdf2_sha256 for compatibility with modern Python environments,
# while still accepting older bcrypt hashes if they already exist.
pwd_context = CryptContext(
    schemes=["pbkdf2_sha256", "bcrypt"],
    deprecated="auto",
)


def hash_password(password: str) -> str:
    """Hash a password using bcrypt.
    
    Args:
        password: Plain text password to hash.
        
    Returns:
        Hashed password string.
        
    Example:
        hashed = hash_password("my_secure_password")
    """
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash.
    
    Args:
        plain_password: Plain text password to verify.
        hashed_password: Hashed password to compare against.
        
    Returns:
        True if password matches, False otherwise.
        
    Example:
        if verify_password("my_password", stored_hash):
            print("Password is correct")
    """
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(
    data: Dict[str, Any],
    expires_delta: Optional[timedelta] = None,
) -> str:
    """Create a JWT access token.
    
    Args:
        data: Dictionary of claims to encode in the token.
        expires_delta: Optional custom expiration time. If not provided,
            uses ACCESS_TOKEN_EXPIRE_MINUTES from settings.
            
    Returns:
        Encoded JWT token string.
        
    Example:
        token = create_access_token({"sub": str(user.id), "email": user.email})
    """
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(
            minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
        )
    
    to_encode.update({
        "exp": expire,
        "iat": datetime.now(timezone.utc),
    })
    
    encoded_jwt = jwt.encode(
        to_encode,
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM,
    )
    
    return encoded_jwt


def decode_access_token(token: str) -> Dict[str, Any]:
    """Decode and validate a JWT access token.
    
    Args:
        token: JWT token string to decode.
        
    Returns:
        Dictionary of claims from the token.
        
    Raises:
        AuthenticationError: If token is invalid, expired, or malformed.
        
    Example:
        try:
            payload = decode_access_token(token)
            user_id = payload.get("sub")
        except AuthenticationError:
            print("Invalid token")
    """
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM],
        )
        return payload
    except JWTError as e:
        raise AuthenticationError(
            message="Could not validate credentials",
            details={"error": str(e)},
        )


def create_refresh_token(
    data: Dict[str, Any],
    expires_delta: Optional[timedelta] = None,
) -> str:
    """Create a JWT refresh token with longer expiration.
    
    Args:
        data: Dictionary of claims to encode in the token.
        expires_delta: Optional custom expiration time. Defaults to 7 days.
            
    Returns:
        Encoded JWT refresh token string.
    """
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(days=7)
    
    to_encode.update({
        "exp": expire,
        "iat": datetime.now(timezone.utc),
        "type": "refresh",
    })
    
    encoded_jwt = jwt.encode(
        to_encode,
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM,
    )
    
    return encoded_jwt


def get_token_payload(token: str) -> Optional[Dict[str, Any]]:
    """Get token payload without raising on invalid tokens.
    
    Useful for checking token validity without exception handling.
    
    Args:
        token: JWT token string to decode.
        
    Returns:
        Dictionary of claims if valid, None otherwise.
    """
    try:
        return decode_access_token(token)
    except AuthenticationError:
        return None

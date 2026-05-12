"""Authentication API endpoints.

Handles user registration, login, and profile retrieval.
"""
import asyncio
import re
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError, OperationalError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.core.security import create_access_token, hash_password, verify_password
from app.models.user import User
from app.services.saas import normalize_plan
from app.schemas.user import TokenResponse, UserCreate, UserResponse


router = APIRouter()
REGISTER_LOCK_RETRIES = 3
DUMMY_PASSWORD_HASH = hash_password("smart-scraper-auth-dummy-password-v1")


def _validate_password_strength(password: str) -> dict:
    """Validate password meets minimum strength requirements."""
    if len(password) < 10:
        return {"valid": False, "reason": "Password must be at least 10 characters"}

    if not any(c.islower() for c in password):
        return {"valid": False, "reason": "Password must contain at least one lowercase letter"}

    if not any(c.isupper() for c in password):
        return {"valid": False, "reason": "Password must contain at least one uppercase letter"}

    if not any(c.isdigit() for c in password):
        return {"valid": False, "reason": "Password must contain at least one digit"}

    if not re.search(r"[^A-Za-z0-9]", password):
        return {"valid": False, "reason": "Password must contain at least one special character"}

    return {"valid": True, "reason": ""}



@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user",
)
async def register(
    user_data: UserCreate,
    db: AsyncSession = Depends(get_db),
) -> UserResponse:
    """Register a new user account.
    
    Creates a new user with the provided email and password.
    Password is hashed before storage.
    
    Args:
        user_data: User registration data (email, password).
        db: Database session.
        
    Returns:
        UserResponse: The created user data.
        
    Raises:
        HTTPException 409: If email is already registered.
    """
    # Validate password strength
    password_validation = _validate_password_strength(user_data.password)
    if not password_validation["valid"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Password is too weak: {password_validation['reason']}",
        )
    
    # Create new user with hashed password
    hashed_pwd = hash_password(user_data.password)
    new_user = User(
        email=user_data.email.strip().lower(),
        hashed_password=hashed_pwd,
        is_active=True,
        plan=normalize_plan("free"),
    )
    
    db.add(new_user)
    for attempt in range(REGISTER_LOCK_RETRIES + 1):
        try:
            await db.commit()
            break
        except IntegrityError as exc:
            await db.rollback()
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Email already registered",
            ) from exc
        except OperationalError as exc:
            await db.rollback()
            if "database is locked" not in str(exc).lower() or attempt >= REGISTER_LOCK_RETRIES:
                raise
            await asyncio.sleep(0.2 * (attempt + 1))
            db.add(new_user)
    await db.refresh(new_user)
    
    return UserResponse.model_validate(new_user)


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Authenticate and get access token",
)
async def login(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    """Authenticate user and return JWT access token.
    
    Uses OAuth2 password flow. The username field should contain the email.
    
    Args:
        form_data: OAuth2 form with username (email) and password.
        db: Database session.
        
    Returns:
        TokenResponse: JWT access token.
        
    Raises:
        HTTPException 401: If credentials are invalid.
    """
    # Find user by email (username field contains email)
    normalized_username = form_data.username.strip().lower()
    if not normalized_username:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    stmt = select(User).where(func.lower(User.email) == normalized_username)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    # Always verify against a hash, even when the user doesn't exist, to reduce
    # timing differences that can leak account existence.
    comparison_hash = user.hashed_password if user else DUMMY_PASSWORD_HASH
    password_matches = verify_password(form_data.password, comparison_hash)

    if not user or not password_matches:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Inactive user account",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Create access token with user ID as subject
    access_token = create_access_token(data={"sub": str(user.id)})
    
    return TokenResponse(access_token=access_token, token_type="bearer")


@router.get(
    "/me",
    response_model=UserResponse,
    summary="Get current user profile",
)
async def get_me(
    current_user: User = Depends(get_current_user),
) -> UserResponse:
    """Get the current authenticated user's profile.
    
    Args:
        current_user: The authenticated user from JWT token.
        
    Returns:
        UserResponse: Current user's profile data.
    """
    return UserResponse.model_validate(current_user)

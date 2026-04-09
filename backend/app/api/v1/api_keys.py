from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.models.api_key import ApiKey
from app.models.user import User
from app.schemas.api_key import ApiKeyCreate, ApiKeyCreateResponse, ApiKeyListResponse, ApiKeyResponse
from app.services.saas import build_key_preview, generate_api_key_secret, hash_api_key


router = APIRouter()


def _serialize_api_key(api_key: ApiKey, *, preview: str | None = None) -> ApiKeyResponse:
    return ApiKeyResponse(
        id=api_key.id,
        user_id=api_key.user_id,
        name=api_key.name,
        is_active=api_key.is_active,
        created_at=api_key.created_at,
        key_preview=preview or "Stored securely",
    )


@router.post("", response_model=ApiKeyCreateResponse, status_code=status.HTTP_201_CREATED)
async def create_api_key(
    payload: ApiKeyCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ApiKeyCreateResponse:
    raw_key = generate_api_key_secret()
    api_key = ApiKey(
        user_id=current_user.id,
        key=hash_api_key(raw_key),
        name=payload.name.strip(),
        is_active=True,
    )
    db.add(api_key)
    await db.commit()
    await db.refresh(api_key)

    response = _serialize_api_key(api_key, preview=build_key_preview(raw_key))
    return ApiKeyCreateResponse(**response.model_dump(), api_key=raw_key, key=raw_key)


@router.get("", response_model=ApiKeyListResponse)
async def list_api_keys(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ApiKeyListResponse:
    total = (
        await db.execute(select(func.count(ApiKey.id)).where(ApiKey.user_id == current_user.id))
    ).scalar() or 0
    result = await db.execute(
        select(ApiKey)
        .where(ApiKey.user_id == current_user.id)
        .order_by(ApiKey.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    api_keys = result.scalars().all()
    return ApiKeyListResponse(api_keys=[_serialize_api_key(item) for item in api_keys], total=int(total))


@router.delete("/{api_key_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_api_key(
    api_key_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    result = await db.execute(
        select(ApiKey).where(ApiKey.id == api_key_id, ApiKey.user_id == current_user.id)
    )
    api_key = result.scalar_one_or_none()
    if api_key is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="API key not found")
    await db.delete(api_key)
    await db.commit()

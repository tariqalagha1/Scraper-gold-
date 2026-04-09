from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.models.user import User
from app.schemas.credential import CredentialCreate, CredentialListResponse, CredentialResponse
from app.services.user_credentials import (
    delete_user_credential,
    list_user_credentials,
    serialize_credential,
    upsert_user_credential,
)


router = APIRouter()


@router.post("", response_model=CredentialResponse, status_code=status.HTTP_201_CREATED)
async def create_or_update_credential(
    payload: CredentialCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CredentialResponse:
    try:
        credential = await upsert_user_credential(
            db,
            user_id=current_user.id,
            provider=payload.provider,
            api_key=payload.api_key,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return serialize_credential(credential)


@router.get("", response_model=CredentialListResponse)
async def list_credentials(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CredentialListResponse:
    credentials, total = await list_user_credentials(db, user_id=current_user.id, skip=skip, limit=limit)
    return CredentialListResponse(
        credentials=[serialize_credential(item) for item in credentials],
        total=total,
    )


@router.delete("/{provider}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_credential(
    provider: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    deleted = await delete_user_credential(db, user_id=current_user.id, provider=provider)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Credential not found")

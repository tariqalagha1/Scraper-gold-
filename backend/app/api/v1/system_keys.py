from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db, verify_api_key
from app.models.user import User
from app.schemas.system_secret import SystemSecretItem, SystemSecretListResponse, SystemSecretUpdate
from app.services.system_secrets import (
    can_manage_system_secrets,
    delete_system_secret,
    ensure_supported_system_secret,
    list_system_secret_items,
    upsert_system_secret,
)


router = APIRouter(dependencies=[Depends(verify_api_key)])


def _require_system_keys_admin(current_user: User) -> None:
    if can_manage_system_secrets(current_user):
        return
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Only system-key admins can manage global system keys.",
    )


@router.get("", response_model=SystemSecretListResponse)
async def list_system_keys(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> SystemSecretListResponse:
    _require_system_keys_admin(current_user)
    items = await list_system_secret_items(db)
    return SystemSecretListResponse(secrets=items)


@router.put("/{name}", response_model=SystemSecretItem)
async def save_system_key(
    name: str,
    payload: SystemSecretUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> SystemSecretItem:
    _require_system_keys_admin(current_user)
    try:
        normalized_name = ensure_supported_system_secret(name)
        await upsert_system_secret(
            db,
            name=normalized_name,
            value=payload.value,
            updated_by_user_id=current_user.id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    items = await list_system_secret_items(db)
    for item in items:
        if item.name == normalized_name:
            return item
    raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Saved key could not be loaded.")


@router.delete("/{name}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_system_key(
    name: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    _require_system_keys_admin(current_user)
    try:
        deleted = await delete_system_secret(db, name=name)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="System key not found.")


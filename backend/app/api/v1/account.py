from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.models.user import User
from app.schemas.account import AccountSummaryResponse, PlanLimitsResponse, UsageResponse
from app.services.saas import get_plan_limits, get_usage_summary, normalize_plan


router = APIRouter()


@router.get("/usage", response_model=UsageResponse)
async def get_usage(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> UsageResponse:
    return UsageResponse(**(await get_usage_summary(db, current_user.id)))


@router.get("/plan", response_model=PlanLimitsResponse)
async def get_plan(
    current_user: User = Depends(get_current_user),
) -> PlanLimitsResponse:
    normalized_plan = normalize_plan(current_user.plan)
    limits = get_plan_limits(normalized_plan)
    return PlanLimitsResponse(plan=normalized_plan, **limits)


@router.get("/summary", response_model=AccountSummaryResponse)
async def get_account_summary(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AccountSummaryResponse:
    normalized_plan = normalize_plan(current_user.plan)
    limits = get_plan_limits(normalized_plan)
    usage = await get_usage_summary(db, current_user.id)
    return AccountSummaryResponse(
        plan=PlanLimitsResponse(plan=normalized_plan, **limits),
        usage=UsageResponse(**usage),
    )

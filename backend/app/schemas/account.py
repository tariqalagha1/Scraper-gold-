from pydantic import BaseModel, Field


class PlanLimitsResponse(BaseModel):
    plan: str = Field(...)
    max_jobs: int = Field(...)
    max_runs_per_day: int = Field(...)


class UsageResponse(BaseModel):
    total_jobs: int = Field(...)
    total_runs: int = Field(...)
    total_exports: int = Field(...)
    runs_today: int = Field(...)


class AccountSummaryResponse(BaseModel):
    plan: PlanLimitsResponse
    usage: UsageResponse

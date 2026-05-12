"""Schemas for persisted user preferences."""
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


VisibilityOption = Literal["Internal Only", "Client Shared", "Executive Review"]
CategoryOption = Literal["All Workstreams", "Platform", "Intelligence", "Design", "Operations"]


class DashboardNotificationPreferences(BaseModel):
    budget_warnings: bool = True
    overdue_tasks: bool = True
    milestone_alerts: bool = True
    executive_digest: bool = False


class DashboardPreferences(BaseModel):
    visibility: VisibilityOption = "Internal Only"
    category_filter: CategoryOption = "All Workstreams"
    notifications: DashboardNotificationPreferences = Field(default_factory=DashboardNotificationPreferences)
    plan_tags: list[str] = Field(default_factory=lambda: ["Active", "AI Infra", "Priority Review", "Q2 Launch"])


class DashboardPreferencesResponse(BaseModel):
    preferences: DashboardPreferences
    updated_at: datetime | None = None

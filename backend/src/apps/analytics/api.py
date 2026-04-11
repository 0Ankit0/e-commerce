"""Analytics API endpoints.

Provides server-side feature-flag resolution so clients don't need to
embed PostHog API keys.  All endpoints require authentication.
"""
from datetime import date
from typing import Any
from fastapi import APIRouter, Depends

from src.apps.analytics.dependencies import get_analytics
from src.apps.analytics.service import AnalyticsService
from src.apps.iam.api.deps import get_current_user, get_db
from src.apps.iam.models.user import User
from src.apps.iam.utils.hashid import decode_id_or_404
from src.apps.logistics.services import (
    build_branch_kpi_drilldown,
    build_branch_kpi_snapshot,
    resolve_user_branch_scope,
)
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/analytics", tags=["Analytics"])


@router.get(
    "/feature-flags/",
    summary="Get all feature flags for the current user",
    description="Returns all PostHog (or configured provider) feature flags evaluated for the authenticated user.",
)
async def get_feature_flags(
    current_user: User = Depends(get_current_user),
    analytics: AnalyticsService = Depends(get_analytics),
) -> dict[str, Any]:
    flags = await analytics.get_all_feature_flags(str(current_user.id))
    return {"flags": flags, "analytics_enabled": analytics.enabled}


@router.get(
    "/feature-flags/{flag_key}/",
    summary="Get a single feature flag for the current user",
)
async def get_feature_flag(
    flag_key: str,
    current_user: User = Depends(get_current_user),
    analytics: AnalyticsService = Depends(get_analytics),
) -> dict[str, Any]:
    value = await analytics.get_feature_flag(str(current_user.id), flag_key)
    return {"flag_key": flag_key, "value": value, "analytics_enabled": analytics.enabled}


@router.get("/branch-kpis/snapshot")
async def get_branch_kpi_snapshot(
    branch_id: str | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    agent_id: str | None = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, object]:
    allowed_branch_ids = await resolve_user_branch_scope(current_user, db)
    return await build_branch_kpi_snapshot(
        db=db,
        branch_id=decode_id_or_404(branch_id) if branch_id else None,
        allowed_branch_ids=allowed_branch_ids,
        agent_id=decode_id_or_404(agent_id) if agent_id else None,
        date_from=date_from,
        date_to=date_to,
    )


@router.get("/branch-kpis/drilldown")
async def get_branch_kpi_drilldown(
    branch_id: str | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    agent_id: str | None = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, object]:
    allowed_branch_ids = await resolve_user_branch_scope(current_user, db)
    return await build_branch_kpi_drilldown(
        db=db,
        branch_id=decode_id_or_404(branch_id) if branch_id else None,
        allowed_branch_ids=allowed_branch_ids,
        agent_id=decode_id_or_404(agent_id) if agent_id else None,
        date_from=date_from,
        date_to=date_to,
    )

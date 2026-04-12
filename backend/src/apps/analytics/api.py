"""Analytics API endpoints.

Provides server-side feature-flag resolution so clients don't need to
embed PostHog API keys.  All endpoints require authentication.
"""
from datetime import date, datetime
from typing import Any
from fastapi import APIRouter, Depends

from src.apps.analytics.dependencies import get_analytics
from src.apps.analytics.service import AnalyticsService
from src.apps.iam.api.deps import get_current_active_superuser, get_current_user, get_db
from src.apps.iam.models.user import User
from src.apps.iam.utils.hashid import decode_id_or_404
from src.apps.logistics.services import (
    build_branch_kpi_drilldown,
    build_branch_kpi_snapshot,
    resolve_user_branch_scope,
)
from sqlalchemy.ext.asyncio import AsyncSession
from src.apps.notification.models.notification_delivery import NotificationDeliveryChannel
from src.apps.notification.services.notification import (
    detect_delivery_anomalies,
    get_admin_monitoring_dashboard,
    get_admin_monitoring_drilldown,
    get_channel_delivery_trends,
    get_template_delivery_trends,
)
from src.apps.notification.services.delivery_analytics import (
    evaluate_delivery_alerts,
    get_notification_analytics_dashboard,
    get_notification_delivery_analytics,
    list_delivery_alerts,
    summarize_and_prune_delivery_events,
)

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
    zone_id: str | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    timezone: str = "UTC",
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
        zone_id=decode_id_or_404(zone_id) if zone_id else None,
        date_from=date_from,
        date_to=date_to,
        timezone_name=timezone,
    )


@router.get("/branch-kpis/drilldown")
async def get_branch_kpi_drilldown(
    branch_id: str | None = None,
    zone_id: str | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    timezone: str = "UTC",
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
        zone_id=decode_id_or_404(zone_id) if zone_id else None,
        date_from=date_from,
        date_to=date_to,
        timezone_name=timezone,
    )


@router.get("/notifications/channels/performance")
async def get_notification_channel_performance(
    date_from: date | None = None,
    date_to: date | None = None,
    channel: NotificationDeliveryChannel | None = None,
    skip: int = 0,
    limit: int = 50,
    _: User = Depends(get_current_active_superuser),
    db: AsyncSession = Depends(get_db),
) -> dict[str, object]:
    return await get_channel_delivery_trends(
        db=db,
        date_from=date_from.isoformat() if date_from else None,
        date_to=date_to.isoformat() if date_to else None,
        channel=channel,
        skip=skip,
        limit=limit,
    )


@router.get("/notifications/templates/performance")
async def get_notification_template_performance(
    date_from: date | None = None,
    date_to: date | None = None,
    channel: NotificationDeliveryChannel | None = None,
    template: str | None = None,
    skip: int = 0,
    limit: int = 50,
    _: User = Depends(get_current_active_superuser),
    db: AsyncSession = Depends(get_db),
) -> dict[str, object]:
    return await get_template_delivery_trends(
        db=db,
        date_from=date_from.isoformat() if date_from else None,
        date_to=date_to.isoformat() if date_to else None,
        channel=channel,
        template=template,
        skip=skip,
        limit=limit,
    )


@router.get("/notifications/delivery/analytics")
async def get_notification_delivery_analytics_endpoint(
    date_from: date | None = None,
    date_to: date | None = None,
    channel: NotificationDeliveryChannel | None = None,
    template: str | None = None,
    _: User = Depends(get_current_active_superuser),
    db: AsyncSession = Depends(get_db),
) -> dict[str, object]:
    return await get_notification_delivery_analytics(
        db=db,
        date_from=datetime.combine(date_from, datetime.min.time()) if date_from else None,
        date_to=datetime.combine(date_to, datetime.max.time()) if date_to else None,
        channel=channel,
        template=template,
    )


@router.get("/notifications/delivery/dashboard")
async def get_notification_delivery_dashboard(
    lookback_days: int = 7,
    _: User = Depends(get_current_active_superuser),
    db: AsyncSession = Depends(get_db),
) -> dict[str, object]:
    return await get_notification_analytics_dashboard(db=db, lookback_days=max(1, min(lookback_days, 30)))


@router.get("/notifications/delivery/monitoring/dashboard")
async def get_notification_monitoring_dashboard(
    date_from: date | None = None,
    date_to: date | None = None,
    _: User = Depends(get_current_active_superuser),
    db: AsyncSession = Depends(get_db),
) -> dict[str, object]:
    return await get_admin_monitoring_dashboard(
        db=db,
        date_from=date_from.isoformat() if date_from else None,
        date_to=date_to.isoformat() if date_to else None,
    )


@router.get("/notifications/delivery/monitoring/drilldown")
async def get_notification_monitoring_drilldown(
    template: str | None = None,
    provider: str | None = None,
    channel: NotificationDeliveryChannel | None = None,
    limit: int = 100,
    _: User = Depends(get_current_active_superuser),
    db: AsyncSession = Depends(get_db),
) -> dict[str, object]:
    return await get_admin_monitoring_drilldown(
        db=db,
        template=template,
        provider=provider,
        channel=channel,
        limit=max(1, min(limit, 500)),
    )


@router.get("/notifications/delivery/anomalies")
async def get_notification_delivery_anomalies(
    lookback_hours: int = 24,
    failure_spike_threshold: float = 0.35,
    slow_delivery_threshold_ms: float = 15000.0,
    _: User = Depends(get_current_active_superuser),
    db: AsyncSession = Depends(get_db),
) -> dict[str, object]:
    return await detect_delivery_anomalies(
        db=db,
        lookback_hours=max(1, min(lookback_hours, 168)),
        failure_spike_threshold=max(0.01, min(failure_spike_threshold, 1.0)),
        slow_delivery_threshold_ms=max(50.0, slow_delivery_threshold_ms),
    )


@router.post("/notifications/delivery/alerts/evaluate")
async def evaluate_notification_delivery_alerts(
    lookback_minutes: int = 30,
    _: User = Depends(get_current_active_superuser),
    db: AsyncSession = Depends(get_db),
) -> dict[str, object]:
    alerts = await evaluate_delivery_alerts(db=db, lookback_minutes=max(5, min(lookback_minutes, 240)))
    return {"created": len(alerts)}


@router.get("/notifications/delivery/alerts")
async def get_notification_delivery_alerts(
    limit: int = 50,
    _: User = Depends(get_current_active_superuser),
    db: AsyncSession = Depends(get_db),
) -> dict[str, object]:
    alerts = await list_delivery_alerts(db, limit=max(1, min(limit, 200)))
    return {"items": [alert.model_dump() for alert in alerts], "total": len(alerts)}


@router.post("/notifications/delivery/events/retention")
async def execute_notification_delivery_retention(
    _: User = Depends(get_current_active_superuser),
    db: AsyncSession = Depends(get_db),
) -> dict[str, int]:
    return await summarize_and_prune_delivery_events(db)

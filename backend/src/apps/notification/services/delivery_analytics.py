from __future__ import annotations

from datetime import datetime, timedelta
from math import ceil
from statistics import quantiles
from typing import Any

from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.apps.core.config import settings
from src.apps.core.time import utc_now
from src.apps.notification.models.notification import Notification
from src.apps.notification.models.notification_delivery import (
    NotificationDelivery,
    NotificationDeliveryAlert,
    NotificationDeliveryChannel,
    NotificationDeliveryDailySummary,
    NotificationDeliveryEvent,
    NotificationDeliveryEventType,
    NotificationDeliveryStatus,
    NotificationFailureBucket,
)


def normalize_delivery_failure(*, code: str | None, reason: str | None) -> tuple[str, NotificationFailureBucket]:
    value = f"{code or ''} {reason or ''}".lower()
    if any(token in value for token in ("timeout", "503", "502", "outage", "unavailable")):
        return "provider_unavailable", NotificationFailureBucket.PROVIDER_OUTAGE
    if any(token in value for token in ("rate", "throttle", "429")):
        return "rate_limited", NotificationFailureBucket.RATE_LIMITED
    if any(token in value for token in ("invalid", "unregistered", "unknown user", "bad address")):
        return "invalid_recipient", NotificationFailureBucket.INVALID_RECIPIENT
    if any(token in value for token in ("auth", "credential", "forbidden", "401", "403")):
        return "auth_error", NotificationFailureBucket.AUTH_CONFIGURATION
    if "quota" in value:
        return "quota_exceeded", NotificationFailureBucket.QUOTA_EXCEEDED
    if any(token in value for token in ("connection", "network", "dns", "reset by peer")):
        return "network_error", NotificationFailureBucket.NETWORK
    if any(token in value for token in ("policy", "spam", "suppressed", "blocked")):
        return "content_policy", NotificationFailureBucket.CONTENT_POLICY
    return "unknown_error", NotificationFailureBucket.UNKNOWN


async def record_delivery_event(
    db: AsyncSession,
    *,
    delivery: NotificationDelivery,
    event_type: NotificationDeliveryEventType,
    status_before: NotificationDeliveryStatus | None,
    status_after: NotificationDeliveryStatus | None,
    provider_code: str | None = None,
    error_reason: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> NotificationDeliveryEvent:
    normalized_error_code = None
    failure_bucket = None
    if event_type in {NotificationDeliveryEventType.FAILED, NotificationDeliveryEventType.DEAD_LETTERED}:
        normalized_error_code, failure_bucket = normalize_delivery_failure(code=provider_code, reason=error_reason)

    latency_ms = None
    if delivery.queued_at and delivery.delivered_at:
        latency_ms = max(0, int((delivery.delivered_at - delivery.queued_at).total_seconds() * 1000))

    event = NotificationDeliveryEvent(
        delivery_id=delivery.id,
        notification_id=delivery.notification_id,
        user_id=delivery.user_id,
        channel=delivery.channel,
        event_type=event_type,
        status_before=status_before,
        status_after=status_after,
        provider=delivery.provider,
        provider_response_code=provider_code,
        normalized_error_code=normalized_error_code,
        failure_bucket=failure_bucket,
        error_reason=error_reason,
        attempt_count=delivery.attempt_count,
        latency_ms=latency_ms,
        event_metadata_json=metadata or {},
        occurred_at=utc_now(),
    )
    db.add(event)
    return event


async def get_notification_delivery_analytics(
    db: AsyncSession,
    *,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    channel: NotificationDeliveryChannel | None = None,
    template: str | None = None,
) -> dict[str, Any]:
    filters = []
    if date_from:
        filters.append(NotificationDelivery.created_at >= date_from)
    if date_to:
        filters.append(NotificationDelivery.created_at <= date_to)
    if channel is not None:
        filters.append(NotificationDelivery.channel == channel)

    delivery_stmt = select(NotificationDelivery)
    if template:
        delivery_stmt = delivery_stmt.join(Notification, Notification.id == NotificationDelivery.notification_id).where(
            Notification.type == template
        )
    if filters:
        delivery_stmt = delivery_stmt.where(*filters)

    deliveries = (await db.execute(delivery_stmt)).scalars().all()

    total = len(deliveries)
    delivered = len([d for d in deliveries if d.status == NotificationDeliveryStatus.DELIVERED])
    failed = len([d for d in deliveries if d.status in {NotificationDeliveryStatus.FAILED, NotificationDeliveryStatus.DEAD_LETTER}])
    delivery_rate = (delivered / total) if total else 0.0

    latencies = [
        (d.delivered_at - d.queued_at).total_seconds() * 1000
        for d in deliveries
        if d.delivered_at is not None and d.queued_at is not None
    ]
    if len(latencies) >= 2:
        p95_latency_ms = float(quantiles(latencies, n=100)[94])
    elif latencies:
        p95_latency_ms = float(latencies[0])
    else:
        p95_latency_ms = 0.0

    retry_attempts = [d for d in deliveries if d.attempt_count > 1]
    max_attempt = max((d.attempt_count for d in retry_attempts), default=0)
    retry_curve = []
    for attempt in range(2, max_attempt + 1):
        cohort = [d for d in retry_attempts if d.attempt_count >= attempt]
        if not cohort:
            continue
        success_count = len([d for d in cohort if d.status == NotificationDeliveryStatus.DELIVERED])
        retry_curve.append(
            {
                "attempt": attempt,
                "sample_size": len(cohort),
                "success_count": success_count,
                "success_rate": success_count / len(cohort),
            }
        )

    failure_rows = (
        await db.execute(
            select(NotificationDeliveryEvent.failure_bucket, func.count())
            .where(NotificationDeliveryEvent.event_type.in_([NotificationDeliveryEventType.FAILED, NotificationDeliveryEventType.DEAD_LETTERED]))
            .group_by(NotificationDeliveryEvent.failure_bucket)
            .order_by(func.count().desc())
        )
    ).all()

    return {
        "total": total,
        "delivered": delivered,
        "failed": failed,
        "delivery_rate": delivery_rate,
        "p95_latency_ms": p95_latency_ms,
        "retry_success_curve": retry_curve,
        "failure_root_causes": [
            {
                "bucket": bucket.value if bucket else NotificationFailureBucket.UNKNOWN.value,
                "count": count,
                "share": (count / max(failed, 1)),
            }
            for bucket, count in failure_rows
        ],
    }


async def get_notification_analytics_dashboard(db: AsyncSession, *, lookback_days: int = 7) -> dict[str, Any]:
    now = utc_now()
    start = now - timedelta(days=lookback_days)
    previous_start = start - timedelta(days=lookback_days)

    current = await get_notification_delivery_analytics(db, date_from=start, date_to=now)
    previous = await get_notification_delivery_analytics(db, date_from=previous_start, date_to=start)

    channel_rows = (
        await db.execute(
            select(
                NotificationDelivery.channel,
                func.count().label("total"),
                func.sum(case((NotificationDelivery.status == NotificationDeliveryStatus.DELIVERED, 1), else_=0)).label("delivered"),
            )
            .where(NotificationDelivery.created_at >= start)
            .group_by(NotificationDelivery.channel)
        )
    ).all()

    drilldowns = [
        {
            "channel": row.channel.value if hasattr(row.channel, "value") else str(row.channel),
            "total": int(row.total or 0),
            "delivery_rate": (int(row.delivered or 0) / int(row.total or 1)),
        }
        for row in channel_rows
    ]

    return {
        "window": {"from": start.isoformat(), "to": now.isoformat(), "days": lookback_days},
        "summary": current,
        "comparison": {
            "delivery_rate_delta": current["delivery_rate"] - previous["delivery_rate"],
            "p95_latency_delta_ms": current["p95_latency_ms"] - previous["p95_latency_ms"],
            "failed_delta": current["failed"] - previous["failed"],
        },
        "drilldowns": drilldowns,
    }


async def evaluate_delivery_alerts(db: AsyncSession, *, lookback_minutes: int = 30) -> list[NotificationDeliveryAlert]:
    now = utc_now()
    start = now - timedelta(minutes=lookback_minutes)
    rows = (
        await db.execute(
            select(
                NotificationDelivery.provider,
                NotificationDelivery.channel,
                func.count().label("total"),
                func.sum(case((NotificationDelivery.status.in_([NotificationDeliveryStatus.FAILED, NotificationDeliveryStatus.DEAD_LETTER]), 1), else_=0)).label("failed"),
            )
            .where(NotificationDelivery.updated_at >= start)
            .group_by(NotificationDelivery.provider, NotificationDelivery.channel)
        )
    ).all()

    created: list[NotificationDeliveryAlert] = []
    for row in rows:
        total = int(row.total or 0)
        failed = int(row.failed or 0)
        if total < 10:
            continue
        failure_rate = failed / total
        if failure_rate >= settings.NOTIFICATION_ALERT_FAILURE_RATE_THRESHOLD:
            alert = NotificationDeliveryAlert(
                provider=row.provider or "unknown",
                channel=row.channel,
                alert_type="failure_rate_spike",
                severity="critical" if failure_rate > 0.5 else "warning",
                metric_value=failure_rate,
                threshold_value=settings.NOTIFICATION_ALERT_FAILURE_RATE_THRESHOLD,
                message=f"Failure rate {failure_rate:.1%} exceeded threshold for provider {row.provider}",
                observed_window_start=start,
                observed_window_end=now,
                metadata_json={"total": total, "failed": failed},
            )
            db.add(alert)
            created.append(alert)
    await db.commit()
    return created


async def list_delivery_alerts(db: AsyncSession, *, limit: int = 50) -> list[NotificationDeliveryAlert]:
    return (
        await db.execute(
            select(NotificationDeliveryAlert)
            .order_by(NotificationDeliveryAlert.created_at.desc())
            .limit(limit)
        )
    ).scalars().all()


async def summarize_and_prune_delivery_events(db: AsyncSession) -> dict[str, int]:
    retention_cutoff = utc_now() - timedelta(days=settings.NOTIFICATION_EVENT_RETENTION_DAYS)
    stale_events = (
        await db.execute(select(NotificationDeliveryEvent).where(NotificationDeliveryEvent.occurred_at < retention_cutoff))
    ).scalars().all()

    grouped: dict[tuple[str, str, str, str], list[NotificationDeliveryEvent]] = {}
    for event in stale_events:
        day = event.occurred_at.date().isoformat()
        provider = event.provider or "unknown"
        key = (day, event.channel.value, provider, str(event.event_metadata_json.get("template", "unknown")))
        grouped.setdefault(key, []).append(event)

    for (day, channel, provider, template), events in grouped.items():
        latencies = [evt.latency_ms for evt in events if evt.latency_ms is not None]
        p95 = 0.0
        if len(latencies) >= 2:
            idx = min(len(latencies) - 1, ceil(0.95 * len(latencies)) - 1)
            p95 = float(sorted(latencies)[idx])
        elif latencies:
            p95 = float(latencies[0])

        summary = NotificationDeliveryDailySummary(
            day=day,
            channel=NotificationDeliveryChannel(channel),
            template=template,
            provider=provider,
            total_events=len(events),
            delivered_events=len([e for e in events if e.event_type == NotificationDeliveryEventType.DELIVERED]),
            failed_events=len([e for e in events if e.event_type in {NotificationDeliveryEventType.FAILED, NotificationDeliveryEventType.DEAD_LETTERED}]),
            avg_latency_ms=(sum(latencies) / len(latencies)) if latencies else 0.0,
            p95_latency_ms=p95,
            retry_success_count=len([e for e in events if e.event_type == NotificationDeliveryEventType.DELIVERED and e.attempt_count > 1]),
        )
        db.add(summary)

    for event in stale_events:
        await db.delete(event)

    await db.commit()
    return {"summarized_days": len(grouped), "pruned_events": len(stale_events)}

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import func
from sqlmodel import select

from src.apps.iam.api.deps import get_current_active_superuser, get_db
from src.apps.iam.models.user import User
from src.apps.notification.models.sms_quota import (
    SmsQuotaConfig,
    SmsQuotaCounter,
    SmsQuotaPolicyAuditEvent,
    SmsQuotaViolationEvent,
)
from src.apps.notification.services.sms_service import get_or_create_quota_config, reset_sms_quota_counters

router = APIRouter(prefix="/admin/sms-quotas", tags=["notification-quota-admin"])


class SmsQuotaConfigPayload(BaseModel):
    provider: str = Field(default="default", max_length=64)
    per_user_daily_limit: int | None = Field(default=None, ge=1)
    per_tenant_daily_limit: int | None = Field(default=None, ge=1)
    per_phone_window_limit: int | None = Field(default=None, ge=1)
    phone_window_seconds: int = Field(default=600, ge=1)
    per_ip_window_limit: int | None = Field(default=None, ge=1)
    ip_window_seconds: int = Field(default=300, ge=1)
    per_device_window_limit: int | None = Field(default=None, ge=1)
    device_window_seconds: int = Field(default=300, ge=1)
    global_provider_soft_daily_limit: int | None = Field(default=None, ge=1)
    global_provider_daily_limit: int | None = Field(default=None, ge=1)
    soft_throttle_action: str = Field(default="delay", max_length=24)
    hard_throttle_action: str = Field(default="block", max_length=24)
    soft_throttle_delay_seconds: int = Field(default=30, ge=0)
    hard_throttle_delay_seconds: int = Field(default=0, ge=0)
    hard_cooldown_seconds: int = Field(default=900, ge=0)
    trusted_entry_points: list[str] = Field(default_factory=list)
    privileged_override_enabled: bool = True


@router.get("/config/")
async def get_sms_quota_config(
    provider: str = "default",
    _: User = Depends(get_current_active_superuser),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    config = await get_or_create_quota_config(db, provider=provider)
    await db.commit()
    return config.model_dump()


@router.put("/config/")
async def update_sms_quota_config(
    payload: SmsQuotaConfigPayload,
    current_user: User = Depends(get_current_active_superuser),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    config = await get_or_create_quota_config(db, provider=payload.provider)
    config.per_user_daily_limit = payload.per_user_daily_limit
    config.per_tenant_daily_limit = payload.per_tenant_daily_limit
    config.per_phone_window_limit = payload.per_phone_window_limit
    config.phone_window_seconds = payload.phone_window_seconds
    config.per_ip_window_limit = payload.per_ip_window_limit
    config.ip_window_seconds = payload.ip_window_seconds
    config.per_device_window_limit = payload.per_device_window_limit
    config.device_window_seconds = payload.device_window_seconds
    config.global_provider_soft_daily_limit = payload.global_provider_soft_daily_limit
    config.global_provider_daily_limit = payload.global_provider_daily_limit
    config.soft_throttle_action = payload.soft_throttle_action
    config.hard_throttle_action = payload.hard_throttle_action
    config.soft_throttle_delay_seconds = payload.soft_throttle_delay_seconds
    config.hard_throttle_delay_seconds = payload.hard_throttle_delay_seconds
    config.hard_cooldown_seconds = payload.hard_cooldown_seconds
    config.trusted_entry_points_json = {"allow": payload.trusted_entry_points}
    config.privileged_override_enabled = payload.privileged_override_enabled
    config.updated_by_user_id = current_user.id
    config.updated_at = datetime.now(UTC)
    db.add(config)
    db.add(
        SmsQuotaPolicyAuditEvent(
            provider=config.provider,
            actor_user_id=current_user.id,
            action="config_updated",
            changed_fields_json=payload.model_dump(),
            impact_summary_json={
                "trusted_entry_points_count": len(payload.trusted_entry_points),
                "hard_mode": payload.hard_throttle_action,
                "soft_mode": payload.soft_throttle_action,
            },
        )
    )
    await db.commit()
    await db.refresh(config)
    return config.model_dump()


@router.get("/dashboard/")
async def get_sms_quota_dashboard(
    provider: str = "default",
    _: User = Depends(get_current_active_superuser),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    counters = (
        await db.execute(
            select(SmsQuotaCounter)
            .where(SmsQuotaCounter.provider == provider)
            .order_by(SmsQuotaCounter.updated_at.desc())
            .limit(200)
        )
    ).scalars().all()
    violations = (
        await db.execute(
            select(SmsQuotaViolationEvent)
            .where(SmsQuotaViolationEvent.provider == provider)
            .order_by(SmsQuotaViolationEvent.created_at.desc())
            .limit(200)
        )
    ).scalars().all()
    grouped: dict[str, int] = {
        "user_daily": 0,
        "tenant_daily": 0,
        "phone_window": 0,
        "ip_window": 0,
        "device_window": 0,
        "provider_daily_soft": 0,
        "provider_daily": 0,
    }
    for row in counters:
        grouped[row.scope] = grouped.get(row.scope, 0) + row.usage_count
    top_offenders = sorted(counters, key=lambda row: row.usage_count, reverse=True)[:20]
    return {
        "provider": provider,
        "totals": {
            "counters": len(counters),
            "violations": len(violations),
            "blocked_attempts": sum(1 for row in violations if row.throttle_action in {"block", "cooldown"}),
            "override_violations": sum(1 for row in violations if row.override_applied),
        },
        "usage_by_scope": grouped,
        "usage_trends": [
            {
                "window_start": row.window_start.isoformat(),
                "window_end": row.window_end.isoformat(),
                "scope": row.scope,
                "usage_count": row.usage_count,
            }
            for row in counters[:50]
        ],
        "top_offenders": [row.model_dump() for row in top_offenders],
        "active_counters": [row.model_dump() for row in counters],
    }


@router.get("/violations/")
async def list_sms_quota_violations(
    provider: str = "default",
    override_applied: bool | None = Query(default=None),
    limit: int = Query(default=200, ge=1, le=500),
    _: User = Depends(get_current_active_superuser),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    query = select(SmsQuotaViolationEvent).where(SmsQuotaViolationEvent.provider == provider)
    if override_applied is not None:
        query = query.where(SmsQuotaViolationEvent.override_applied == override_applied)
    rows = (await db.execute(query.order_by(SmsQuotaViolationEvent.created_at.desc()).limit(limit))).scalars().all()
    return {"items": [row.model_dump() for row in rows], "count": len(rows)}


@router.get("/incidents/export/")
async def export_sms_quota_incidents(
    provider: str = "default",
    limit: int = Query(default=500, ge=1, le=2000),
    _: User = Depends(get_current_active_superuser),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    rows = (
        await db.execute(
            select(SmsQuotaViolationEvent)
            .where(SmsQuotaViolationEvent.provider == provider)
            .order_by(SmsQuotaViolationEvent.created_at.desc())
            .limit(limit)
        )
    ).scalars().all()
    incidents = [
        {
            "id": row.id,
            "created_at": row.created_at.isoformat(),
            "scope": row.scope,
            "severity": row.severity,
            "throttle_action": row.throttle_action,
            "delay_seconds": row.delay_seconds,
            "cooldown_until": row.cooldown_until.isoformat() if row.cooldown_until else None,
            "attempted_count": row.attempted_count,
            "limit_count": row.limit_count,
            "provider": row.provider,
            "tenant_id": row.tenant_id,
            "user_id": row.user_id,
            "override_applied": row.override_applied,
            "reason": row.reason,
        }
        for row in rows
    ]
    return {"provider": provider, "count": len(incidents), "items": incidents}


@router.get("/audit/")
async def list_sms_quota_audit_events(
    provider: str = "default",
    limit: int = Query(default=200, ge=1, le=1000),
    _: User = Depends(get_current_active_superuser),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    rows = (
        await db.execute(
            select(SmsQuotaPolicyAuditEvent)
            .where(SmsQuotaPolicyAuditEvent.provider == provider)
            .order_by(SmsQuotaPolicyAuditEvent.created_at.desc())
            .limit(limit)
        )
    ).scalars().all()
    return {"provider": provider, "count": len(rows), "items": [row.model_dump() for row in rows]}


@router.get("/audit/export/")
async def export_sms_quota_audit_events(
    provider: str = "default",
    _: User = Depends(get_current_active_superuser),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    rows = (
        await db.execute(
            select(SmsQuotaPolicyAuditEvent)
            .where(SmsQuotaPolicyAuditEvent.provider == provider)
            .order_by(SmsQuotaPolicyAuditEvent.created_at.desc())
            .limit(5000)
        )
    ).scalars().all()
    impact = (
        await db.execute(
            select(
                SmsQuotaViolationEvent.throttle_action,
                func.count(SmsQuotaViolationEvent.id),
            )
            .where(SmsQuotaViolationEvent.provider == provider)
            .group_by(SmsQuotaViolationEvent.throttle_action)
        )
    ).all()
    return {
        "provider": provider,
        "count": len(rows),
        "impact_by_action": {action: count for action, count in impact},
        "items": [row.model_dump() for row in rows],
    }


@router.post("/counters/reset/")
async def reset_sms_counters(
    provider: str = "default",
    _: User = Depends(get_current_active_superuser),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    deleted = await reset_sms_quota_counters(db, provider=provider)
    await db.commit()
    return {"deleted": deleted, "provider": provider}

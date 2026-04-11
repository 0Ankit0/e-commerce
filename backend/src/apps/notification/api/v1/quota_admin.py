from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from src.apps.iam.api.deps import get_current_active_superuser, get_db
from src.apps.iam.models.user import User
from src.apps.notification.models.sms_quota import SmsQuotaConfig, SmsQuotaCounter, SmsQuotaViolationEvent
from src.apps.notification.services.sms_service import get_or_create_quota_config, reset_sms_quota_counters

router = APIRouter(prefix="/admin/sms-quotas", tags=["notification-quota-admin"])


class SmsQuotaConfigPayload(BaseModel):
    provider: str = Field(default="default", max_length=64)
    per_user_daily_limit: int | None = Field(default=None, ge=1)
    per_ip_window_limit: int | None = Field(default=None, ge=1)
    ip_window_seconds: int = Field(default=300, ge=1)
    global_provider_daily_limit: int | None = Field(default=None, ge=1)
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
    config.per_ip_window_limit = payload.per_ip_window_limit
    config.ip_window_seconds = payload.ip_window_seconds
    config.global_provider_daily_limit = payload.global_provider_daily_limit
    config.privileged_override_enabled = payload.privileged_override_enabled
    config.updated_by_user_id = current_user.id
    config.updated_at = datetime.now(UTC)
    db.add(config)
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
    grouped: dict[str, int] = {"user_daily": 0, "ip_window": 0, "provider_daily": 0}
    for row in counters:
        grouped[row.scope] = grouped.get(row.scope, 0) + row.usage_count
    return {
        "provider": provider,
        "totals": {
            "counters": len(counters),
            "violations": len(violations),
            "override_violations": sum(1 for row in violations if row.override_applied),
        },
        "usage_by_scope": grouped,
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


@router.post("/counters/reset/")
async def reset_sms_counters(
    provider: str = "default",
    _: User = Depends(get_current_active_superuser),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    deleted = await reset_sms_quota_counters(db, provider=provider)
    await db.commit()
    return {"deleted": deleted, "provider": provider}

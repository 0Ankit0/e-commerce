from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from src.apps.communications import get_communications_service
from src.apps.communications.delivery_observability import get_delivery_analytics, reconcile_webhook_event
from src.apps.communications.models import (
    ChannelQuotaOverrideAudit,
    ChannelQuotaPolicy,
    ChannelQuotaUsage,
    EmailDeliveryDeadLetter,
    EmailDeliveryMessage,
    EmailMessageLifecycleStatus,
)
from src.apps.communications.quota import QuotaContext, derive_scope, list_matching_policies
from src.apps.core.config import NON_RUNTIME_EDITABLE_SETTING_KEYS, settings
from src.apps.core.models import GeneralSetting
from src.apps.core.settings_store import (
    build_general_setting_payload,
    get_environment_settings_snapshot,
    get_general_settings,
)
from src.apps.iam.api.deps import get_current_active_superuser, get_db
from src.apps.iam.models.user import User
from src.apps.iam.security import PrivilegedAction, enforce_privileged_action
from src.apps.system.schemas import GeneralSettingRead

router = APIRouter(prefix="/system", tags=["system"])


class GeneralSettingUpdateRequest(BaseModel):
    db_value: str | None = None
    use_db_value: bool = True




class ChannelQuotaPolicyPayload(BaseModel):
    channel: str = Field(default="sms", max_length=32)
    tenant_id: int | None = None
    user_id: int | None = None
    limit_count: int = Field(ge=1)
    window_seconds: int = Field(ge=1)
    timezone: str = Field(default="UTC", max_length=64)
    enabled: bool = True


class ChannelQuotaPolicyOverridePayload(BaseModel):
    limit_count: int | None = Field(default=None, ge=1)
    enabled: bool | None = None
    reason: str = Field(default="", max_length=512)


class ChannelQuotaCheckPayload(BaseModel):
    channel: str = Field(default="sms", max_length=32)
    tenant_id: int | None = None
    user_id: int | None = None

class EmailWebhookPayload(BaseModel):
    event_id: str = Field(min_length=1, max_length=255)
    message_id: str = Field(min_length=1, max_length=255)
    status: str = Field(min_length=1, max_length=64)
    occurred_at: datetime | None = None
    failure_reason: str | None = None
    payload: dict[str, Any] = Field(default_factory=dict)


_WEBHOOK_STATUS_MAP: dict[str, EmailMessageLifecycleStatus] = {
    "queued": EmailMessageLifecycleStatus.QUEUED,
    "accepted": EmailMessageLifecycleStatus.QUEUED,
    "processing": EmailMessageLifecycleStatus.SENT,
    "sending": EmailMessageLifecycleStatus.SENT,
    "sent": EmailMessageLifecycleStatus.SENT,
    "delivered": EmailMessageLifecycleStatus.DELIVERED,
    "hard_bounced": EmailMessageLifecycleStatus.BOUNCED,
    "soft_bounced": EmailMessageLifecycleStatus.BOUNCED,
    "bounced": EmailMessageLifecycleStatus.BOUNCED,
    "blocked": EmailMessageLifecycleStatus.FAILED,
    "dropped": EmailMessageLifecycleStatus.FAILED,
    "rejected": EmailMessageLifecycleStatus.FAILED,
    "failed": EmailMessageLifecycleStatus.FAILED,
    "spam": EmailMessageLifecycleStatus.COMPLAINED,
    "complained": EmailMessageLifecycleStatus.COMPLAINED,
    "complaint": EmailMessageLifecycleStatus.COMPLAINED,
}


def _normalize_webhook_status(raw_status: str) -> EmailMessageLifecycleStatus:
    normalized = raw_status.strip().lower()
    if normalized in _WEBHOOK_STATUS_MAP:
        return _WEBHOOK_STATUS_MAP[normalized]
    try:
        return EmailMessageLifecycleStatus(normalized)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=f"Unsupported webhook status: {raw_status}") from exc


@router.get("/capabilities/")
async def get_capabilities() -> dict:
    return get_communications_service().get_capabilities().model_dump()


@router.get("/providers/")
async def get_providers() -> dict:
    return {
        "providers": [
            status.model_dump() for status in get_communications_service().get_provider_statuses()
        ]
    }


@router.get("/general-settings/", response_model=list[GeneralSettingRead])
async def get_general_settings_status(
    db: AsyncSession = Depends(get_db),
) -> list[GeneralSettingRead]:
    rows = await get_general_settings(db)
    return [
        GeneralSettingRead.model_validate(item)
        for item in build_general_setting_payload(rows, public_only=True)
    ]


@router.get("/admin/settings/")
async def get_admin_settings(
    _: User = Depends(get_current_active_superuser),
    db: AsyncSession = Depends(get_db),
) -> list[dict]:
    rows = await get_general_settings(db)
    return build_general_setting_payload(rows, public_only=False)


@router.patch("/admin/settings/{key}")
async def update_admin_setting(
    key: str,
    payload: GeneralSettingUpdateRequest,
    request: Request,
    current_user: User = Depends(get_current_active_superuser),
    db: AsyncSession = Depends(get_db),
) -> dict:
    await enforce_privileged_action(
        db=db,
        request=request,
        current_user=current_user,
        action=PrivilegedAction.SECURITY_SETTINGS_EDIT,
    )
    setting = (await db.execute(select(GeneralSetting).where(GeneralSetting.key == key))).scalars().first()
    env_snapshot = get_environment_settings_snapshot()
    if setting is None and key not in env_snapshot:
        raise HTTPException(status_code=404, detail="Setting not found")
    if setting is None:
        setting = GeneralSetting(
            key=key,
            env_value=env_snapshot.get(key),
            is_runtime_editable=key not in NON_RUNTIME_EDITABLE_SETTING_KEYS,
        )
    if setting is None:
        raise HTTPException(status_code=404, detail="Setting not found")
    if not setting.is_runtime_editable:
        raise HTTPException(status_code=400, detail="Setting is not runtime editable")
    setting.db_value = payload.db_value
    setting.use_db_value = payload.use_db_value
    db.add(setting)
    await db.commit()
    return {"key": key, "db_value": setting.db_value, "use_db_value": setting.use_db_value}


@router.post("/webhooks/email/{provider}/")
async def ingest_email_delivery_webhook(
    provider: str,
    webhook: EmailWebhookPayload,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    status = _normalize_webhook_status(webhook.status)
    event, duplicate = await reconcile_webhook_event(
        db,
        provider=provider,
        provider_event_id=webhook.event_id,
        provider_message_id=webhook.message_id,
        status=status,
        occurred_at=webhook.occurred_at,
        payload=webhook.payload,
        failure_reason=webhook.failure_reason,
    )
    return {
        "accepted": True,
        "duplicate": duplicate,
        "out_of_order": event.out_of_order,
        "event_id": event.id,
    }


@router.get("/admin/communications/delivery/analytics/")
async def get_admin_delivery_analytics(
    from_dt: datetime | None = None,
    to_dt: datetime | None = None,
    _: User = Depends(get_current_active_superuser),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    return await get_delivery_analytics(db, from_dt=from_dt, to_dt=to_dt)


@router.get("/admin/communications/delivery/messages/")
async def list_delivery_messages(
    status: EmailMessageLifecycleStatus | None = None,
    skip: int = 0,
    limit: int = 50,
    _: User = Depends(get_current_active_superuser),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    query = select(EmailDeliveryMessage)
    if status:
        query = query.where(EmailDeliveryMessage.status == status)
    query = query.order_by(EmailDeliveryMessage.updated_at.desc()).offset(skip).limit(limit)
    items = (await db.execute(query)).scalars().all()
    return {
        "items": [item.model_dump() for item in items],
        "count": len(items),
    }


@router.get("/admin/communications/delivery/dead-letters/")
async def list_dead_letters(
    skip: int = 0,
    limit: int = 50,
    _: User = Depends(get_current_active_superuser),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    query = select(EmailDeliveryDeadLetter).order_by(EmailDeliveryDeadLetter.created_at.desc()).offset(skip).limit(limit)
    items = (await db.execute(query)).scalars().all()
    return {
        "items": [item.model_dump() for item in items],
        "count": len(items),
    }


@router.get("/maps/config/")
async def get_maps_config() -> dict:
    return get_communications_service().get_map_public_config()


@router.get("/health/")
async def health() -> dict:
    return {"status": "ok", "service": settings.PROJECT_NAME}


@router.get("/ready/")
async def ready() -> dict:
    return {"ready": True, "project": settings.PROJECT_NAME}


@router.get("/admin/communications/quotas/policies/")
async def list_quota_policies(
    channel: str | None = None,
    tenant_id: int | None = None,
    user_id: int | None = None,
    _: User = Depends(get_current_active_superuser),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    query = select(ChannelQuotaPolicy)
    if channel:
        query = query.where(ChannelQuotaPolicy.channel == channel)
    if tenant_id is not None:
        query = query.where(ChannelQuotaPolicy.tenant_id == tenant_id)
    if user_id is not None:
        query = query.where(ChannelQuotaPolicy.user_id == user_id)
    items = (await db.execute(query.order_by(ChannelQuotaPolicy.channel, ChannelQuotaPolicy.window_seconds))).scalars().all()
    return {"items": [item.model_dump() for item in items], "count": len(items)}


@router.post("/admin/communications/quotas/policies/")
async def create_quota_policy(
    payload: ChannelQuotaPolicyPayload,
    _: User = Depends(get_current_active_superuser),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    policy = ChannelQuotaPolicy(
        channel=payload.channel,
        tenant_id=payload.tenant_id,
        user_id=payload.user_id,
        scope=derive_scope(tenant_id=payload.tenant_id, user_id=payload.user_id),
        limit_count=payload.limit_count,
        window_seconds=payload.window_seconds,
        timezone=payload.timezone,
        enabled=payload.enabled,
    )
    db.add(policy)
    await db.commit()
    await db.refresh(policy)
    return policy.model_dump()


@router.patch("/admin/communications/quotas/policies/{policy_id}/override/")
async def override_quota_policy(
    policy_id: int,
    payload: ChannelQuotaPolicyOverridePayload,
    current_user: User = Depends(get_current_active_superuser),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    policy = await db.get(ChannelQuotaPolicy, policy_id)
    if policy is None:
        raise HTTPException(status_code=404, detail="Quota policy not found")

    before = policy.model_dump()
    if payload.limit_count is not None:
        policy.limit_count = payload.limit_count
    if payload.enabled is not None:
        policy.enabled = payload.enabled
    policy.updated_at = datetime.now()

    db.add(policy)
    db.add(
        ChannelQuotaOverrideAudit(
            policy_id=policy.id,
            actor_user_id=current_user.id,
            action="manual_override",
            reason=payload.reason,
            before_json=before,
            after_json=policy.model_dump(),
            metadata_json={"channel": policy.channel},
        )
    )
    await db.commit()
    await db.refresh(policy)
    return policy.model_dump()


@router.get("/admin/communications/quotas/usage/")
async def list_quota_usage(
    channel: str = "sms",
    tenant_id: int | None = None,
    user_id: int | None = None,
    _: User = Depends(get_current_active_superuser),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    policies = await list_matching_policies(db, context=QuotaContext(channel=channel, tenant_id=tenant_id, user_id=user_id))
    if not policies:
        return {"items": [], "count": 0}

    policy_ids = [int(item.id) for item in policies if item.id is not None]
    usage_rows = (
        await db.execute(
            select(ChannelQuotaUsage)
            .where(ChannelQuotaUsage.policy_id.in_(policy_ids))
            .order_by(ChannelQuotaUsage.window_end.desc())
            .limit(200)
        )
    ).scalars().all()
    return {"items": [row.model_dump() for row in usage_rows], "count": len(usage_rows)}


@router.get("/admin/communications/quotas/audit/")
async def list_quota_override_audit(
    policy_id: int | None = None,
    _: User = Depends(get_current_active_superuser),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    query = select(ChannelQuotaOverrideAudit).order_by(ChannelQuotaOverrideAudit.created_at.desc())
    if policy_id is not None:
        query = query.where(ChannelQuotaOverrideAudit.policy_id == policy_id)
    rows = (await db.execute(query.limit(200))).scalars().all()
    return {"items": [row.model_dump() for row in rows], "count": len(rows)}

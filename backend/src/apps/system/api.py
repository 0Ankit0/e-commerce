from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from src.apps.communications import get_communications_service
from src.apps.communications.delivery_observability import get_delivery_analytics, reconcile_webhook_event
from src.apps.communications.models import EmailDeliveryDeadLetter, EmailDeliveryMessage, EmailMessageLifecycleStatus
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


class EmailWebhookPayload(BaseModel):
    event_id: str = Field(min_length=1, max_length=255)
    message_id: str = Field(min_length=1, max_length=255)
    status: EmailMessageLifecycleStatus
    occurred_at: datetime | None = None
    failure_reason: str | None = None
    payload: dict[str, Any] = Field(default_factory=dict)


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
    event, duplicate = await reconcile_webhook_event(
        db,
        provider=provider,
        provider_event_id=webhook.event_id,
        provider_message_id=webhook.message_id,
        status=webhook.status,
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

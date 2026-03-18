from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from src.apps.communications import get_communications_service
from src.apps.core.config import NON_RUNTIME_EDITABLE_SETTING_KEYS, settings
from src.apps.core.models import GeneralSetting
from src.apps.core.settings_store import (
    build_general_setting_payload,
    get_general_settings,
    get_environment_settings_snapshot,
)
from src.apps.iam.api.deps import get_current_active_superuser, get_db
from src.apps.iam.models.user import User
from src.apps.system.schemas import GeneralSettingRead

router = APIRouter(prefix="/system", tags=["system"])


class GeneralSettingUpdateRequest(BaseModel):
    db_value: str | None = None
    use_db_value: bool = True


@router.get("/capabilities/")
async def get_capabilities() -> dict:
    return get_communications_service().get_capabilities().model_dump()


@router.get("/providers/")
async def get_providers() -> dict:
    return {
        "providers": [
            status.model_dump()
            for status in get_communications_service().get_provider_statuses()
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
    _: User = Depends(get_current_active_superuser),
    db: AsyncSession = Depends(get_db),
) -> dict:
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


@router.get("/maps/config/")
async def get_maps_config() -> dict:
    return get_communications_service().get_map_public_config()


@router.get("/health/")
async def health() -> dict:
    return {"status": "ok", "service": settings.PROJECT_NAME}


@router.get("/ready/")
async def ready() -> dict:
    return {"ready": True, "project": settings.PROJECT_NAME}

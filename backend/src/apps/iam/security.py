from __future__ import annotations

import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any

from fastapi import HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.apps.core.cache import RedisCache
from src.apps.iam.models.user import User
from src.apps.observability.service import record_privileged_action_audit


class PrivilegedAction(str, Enum):
    ROLE_CREATE = "admin.rbac.create_role"
    ROLE_PERMISSION_CREATE = "admin.rbac.create_permission"
    ROLE_ASSIGN = "admin.rbac.assign_role"
    ROLE_REMOVE = "admin.rbac.remove_role"
    ROLE_PERMISSION_ASSIGN = "admin.rbac.assign_permission"
    ROLE_PERMISSION_REMOVE = "admin.rbac.remove_permission"
    USER_STATUS_EDIT = "admin.users.status_edit"
    PAYOUT_APPROVE = "admin.payout.approve"
    INCIDENT_REVIEW = "admin.observability.incident_review"
    SECURITY_SETTINGS_EDIT = "admin.system.security_settings_edit"


@dataclass(frozen=True)
class PrivilegedActionPolicy:
    action: PrivilegedAction
    required_roles: tuple[str, ...]
    require_step_up: bool
    otp_freshness_seconds: int


PRIVILEGED_ACTION_POLICY_MAP: dict[PrivilegedAction, PrivilegedActionPolicy] = {
    PrivilegedAction.ROLE_CREATE: PrivilegedActionPolicy(
        action=PrivilegedAction.ROLE_CREATE,
        required_roles=("superuser",),
        require_step_up=True,
        otp_freshness_seconds=300,
    ),
    PrivilegedAction.ROLE_PERMISSION_CREATE: PrivilegedActionPolicy(
        action=PrivilegedAction.ROLE_PERMISSION_CREATE,
        required_roles=("superuser",),
        require_step_up=True,
        otp_freshness_seconds=300,
    ),
    PrivilegedAction.ROLE_ASSIGN: PrivilegedActionPolicy(
        action=PrivilegedAction.ROLE_ASSIGN,
        required_roles=("superuser",),
        require_step_up=True,
        otp_freshness_seconds=300,
    ),
    PrivilegedAction.ROLE_REMOVE: PrivilegedActionPolicy(
        action=PrivilegedAction.ROLE_REMOVE,
        required_roles=("superuser",),
        require_step_up=True,
        otp_freshness_seconds=300,
    ),
    PrivilegedAction.ROLE_PERMISSION_ASSIGN: PrivilegedActionPolicy(
        action=PrivilegedAction.ROLE_PERMISSION_ASSIGN,
        required_roles=("superuser",),
        require_step_up=True,
        otp_freshness_seconds=300,
    ),
    PrivilegedAction.ROLE_PERMISSION_REMOVE: PrivilegedActionPolicy(
        action=PrivilegedAction.ROLE_PERMISSION_REMOVE,
        required_roles=("superuser",),
        require_step_up=True,
        otp_freshness_seconds=300,
    ),
    PrivilegedAction.USER_STATUS_EDIT: PrivilegedActionPolicy(
        action=PrivilegedAction.USER_STATUS_EDIT,
        required_roles=("superuser",),
        require_step_up=True,
        otp_freshness_seconds=300,
    ),
    PrivilegedAction.PAYOUT_APPROVE: PrivilegedActionPolicy(
        action=PrivilegedAction.PAYOUT_APPROVE,
        required_roles=("superuser",),
        require_step_up=True,
        otp_freshness_seconds=300,
    ),
    PrivilegedAction.INCIDENT_REVIEW: PrivilegedActionPolicy(
        action=PrivilegedAction.INCIDENT_REVIEW,
        required_roles=("superuser",),
        require_step_up=True,
        otp_freshness_seconds=300,
    ),
    PrivilegedAction.SECURITY_SETTINGS_EDIT: PrivilegedActionPolicy(
        action=PrivilegedAction.SECURITY_SETTINGS_EDIT,
        required_roles=("superuser",),
        require_step_up=True,
        otp_freshness_seconds=300,
    ),
}

_IN_MEMORY_STEP_UP_STORE: dict[str, dict[str, Any]] = {}


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _policy_override_cache_key(action: PrivilegedAction) -> str:
    return f"privileged:policy:{action.value}"


async def resolve_privileged_action_policy(action: PrivilegedAction) -> PrivilegedActionPolicy:
    default_policy = PRIVILEGED_ACTION_POLICY_MAP[action]
    override = await RedisCache.get(_policy_override_cache_key(action))
    if not override:
        return default_policy
    return PrivilegedActionPolicy(
        action=action,
        required_roles=tuple(override.get("required_roles") or list(default_policy.required_roles)),
        require_step_up=bool(override.get("require_step_up", default_policy.require_step_up)),
        otp_freshness_seconds=int(override.get("otp_freshness_seconds", default_policy.otp_freshness_seconds)),
    )


async def override_privileged_action_policy(
    *,
    action: PrivilegedAction,
    require_step_up: bool | None = None,
    otp_freshness_seconds: int | None = None,
) -> PrivilegedActionPolicy:
    base_policy = await resolve_privileged_action_policy(action)
    updated = {
        "action": action.value,
        "required_roles": list(base_policy.required_roles),
        "require_step_up": base_policy.require_step_up if require_step_up is None else require_step_up,
        "otp_freshness_seconds": (
            base_policy.otp_freshness_seconds if otp_freshness_seconds is None else otp_freshness_seconds
        ),
    }
    await RedisCache.set(_policy_override_cache_key(action), updated)
    return await resolve_privileged_action_policy(action)


async def list_privileged_action_policies() -> list[PrivilegedActionPolicy]:
    return [await resolve_privileged_action_policy(action) for action in PrivilegedAction]


async def issue_step_up_token(*, user_id: int, action: PrivilegedAction) -> dict[str, Any]:
    policy = await resolve_privileged_action_policy(action)
    token = secrets.token_urlsafe(32)
    expires_at = _now() + timedelta(seconds=policy.otp_freshness_seconds)
    payload = {
        "user_id": user_id,
        "action": action.value,
        "expires_at": expires_at.isoformat(),
        "issued_at": _now().isoformat(),
    }
    _IN_MEMORY_STEP_UP_STORE[token] = payload
    await RedisCache.set(f"privileged:stepup:{token}", payload, ttl=policy.otp_freshness_seconds)
    return {
        "step_up_token": token,
        "expires_at": expires_at.isoformat(),
        "required_freshness_seconds": policy.otp_freshness_seconds,
        "action": action.value,
    }


async def consume_step_up_token(*, token: str) -> dict[str, Any] | None:
    payload = await RedisCache.get(f"privileged:stepup:{token}")
    if payload is None:
        payload = _IN_MEMORY_STEP_UP_STORE.get(token)
    await RedisCache.delete(f"privileged:stepup:{token}")
    _IN_MEMORY_STEP_UP_STORE.pop(token, None)
    if not payload:
        return None
    try:
        expires_at = datetime.fromisoformat(str(payload.get("expires_at")))
    except Exception:
        return None
    if expires_at <= _now():
        return None
    return payload


async def build_privileged_action_error(action: PrivilegedAction, *, reason: str) -> dict[str, Any]:
    policy = await resolve_privileged_action_policy(action)
    return {
        "code": "OTP_CHALLENGE_REQUIRED",
        "message": "A recent OTP verification is required for this privileged action.",
        "action": action.value,
        "reason": reason,
        "otp": {
            "enforcement_enabled": policy.require_step_up,
            "required_freshness_seconds": policy.otp_freshness_seconds,
        },
    }


async def enforce_privileged_action(
    *,
    db: AsyncSession,
    request: Request,
    current_user: User,
    action: PrivilegedAction,
) -> None:
    policy = await resolve_privileged_action_policy(action)
    role_ok = current_user.is_superuser if "superuser" in policy.required_roles else True
    if not role_ok:
        await record_privileged_action_audit(
            db,
            actor_user_id=current_user.id,
            action=action.value,
            outcome="failure",
            request=request,
            metadata={"reason": "role_requirement_not_met", "required_roles": list(policy.required_roles)},
        )
        await db.commit()
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="The user doesn't have enough privileges")

    if not policy.require_step_up:
        await record_privileged_action_audit(
            db,
            actor_user_id=current_user.id,
            action=action.value,
            outcome="success",
            request=request,
            metadata={"reason": "step_up_not_required"},
        )
        return

    token = request.headers.get("X-Privileged-Auth")
    if not token:
        await record_privileged_action_audit(
            db,
            actor_user_id=current_user.id,
            action=action.value,
            outcome="challenge_required",
            request=request,
            metadata={"reason": "missing_step_up_token"},
        )
        await db.commit()
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=await build_privileged_action_error(action, reason="missing_step_up_token"),
        )

    payload = await consume_step_up_token(token=token)
    if not payload:
        await record_privileged_action_audit(
            db,
            actor_user_id=current_user.id,
            action=action.value,
            outcome="challenge_required",
            request=request,
            metadata={"reason": "expired_or_invalid_step_up_token"},
        )
        await db.commit()
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=await build_privileged_action_error(action, reason="expired_or_invalid_step_up_token"),
        )

    if int(payload.get("user_id", 0)) != current_user.id:
        await record_privileged_action_audit(
            db,
            actor_user_id=current_user.id,
            action=action.value,
            outcome="failure",
            request=request,
            metadata={"reason": "token_user_mismatch"},
        )
        await db.commit()
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=await build_privileged_action_error(action, reason="token_user_mismatch"),
        )

    if payload.get("action") != action.value:
        await record_privileged_action_audit(
            db,
            actor_user_id=current_user.id,
            action=action.value,
            outcome="failure",
            request=request,
            metadata={"reason": "token_action_mismatch"},
        )
        await db.commit()
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=await build_privileged_action_error(action, reason="token_action_mismatch"),
        )

    await record_privileged_action_audit(
        db,
        actor_user_id=current_user.id,
        action=action.value,
        outcome="success",
        request=request,
        metadata={
            "reason": "step_up_validated",
            "step_up_issued_at": payload.get("issued_at"),
            "step_up_expires_at": payload.get("expires_at"),
        },
    )

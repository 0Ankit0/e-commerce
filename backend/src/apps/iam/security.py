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
    ROLE_ASSIGN = "admin.rbac.assign_role"
    ROLE_REMOVE = "admin.rbac.remove_role"
    USER_STATUS_EDIT = "admin.users.status_edit"
    PAYOUT_APPROVE = "admin.payout.approve"
    SECURITY_SETTINGS_EDIT = "admin.system.security_settings_edit"


@dataclass(frozen=True)
class PrivilegedActionPolicy:
    action: PrivilegedAction
    required_roles: tuple[str, ...]
    otp_freshness_seconds: int


PRIVILEGED_ACTION_POLICY_MAP: dict[PrivilegedAction, PrivilegedActionPolicy] = {
    PrivilegedAction.ROLE_ASSIGN: PrivilegedActionPolicy(
        action=PrivilegedAction.ROLE_ASSIGN,
        required_roles=("superuser",),
        otp_freshness_seconds=300,
    ),
    PrivilegedAction.ROLE_REMOVE: PrivilegedActionPolicy(
        action=PrivilegedAction.ROLE_REMOVE,
        required_roles=("superuser",),
        otp_freshness_seconds=300,
    ),
    PrivilegedAction.USER_STATUS_EDIT: PrivilegedActionPolicy(
        action=PrivilegedAction.USER_STATUS_EDIT,
        required_roles=("superuser",),
        otp_freshness_seconds=300,
    ),
    PrivilegedAction.PAYOUT_APPROVE: PrivilegedActionPolicy(
        action=PrivilegedAction.PAYOUT_APPROVE,
        required_roles=("superuser",),
        otp_freshness_seconds=300,
    ),
    PrivilegedAction.SECURITY_SETTINGS_EDIT: PrivilegedActionPolicy(
        action=PrivilegedAction.SECURITY_SETTINGS_EDIT,
        required_roles=("superuser",),
        otp_freshness_seconds=300,
    ),
}

_IN_MEMORY_STEP_UP_STORE: dict[str, dict[str, Any]] = {}


def _now() -> datetime:
    return datetime.now(timezone.utc)


async def issue_step_up_token(*, user_id: int, action: PrivilegedAction) -> dict[str, Any]:
    policy = PRIVILEGED_ACTION_POLICY_MAP[action]
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


def build_privileged_action_error(action: PrivilegedAction) -> dict[str, Any]:
    policy = PRIVILEGED_ACTION_POLICY_MAP[action]
    return {
        "code": "OTP_CHALLENGE_REQUIRED",
        "message": "A recent OTP verification is required for this privileged action.",
        "action": action.value,
        "otp": {
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
    policy = PRIVILEGED_ACTION_POLICY_MAP[action]
    role_ok = current_user.is_superuser if "superuser" in policy.required_roles else True
    if not role_ok:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="The user doesn't have enough privileges")

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
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=build_privileged_action_error(action))

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
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=build_privileged_action_error(action))

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
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=build_privileged_action_error(action))

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
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=build_privileged_action_error(action))

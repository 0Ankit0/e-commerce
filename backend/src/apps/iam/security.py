from __future__ import annotations

import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any

from fastapi import HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.apps.core.cache import RedisCache
from src.apps.core.config import settings
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
    VENDOR_SUSPEND = "admin.vendor.suspend"
    INCIDENT_REVIEW = "admin.observability.incident_review"
    SECURITY_SETTINGS_EDIT = "admin.system.security_settings_edit"
    CONTENT_PROMOTION_PUBLISH = "admin.content.promotion_publish"


@dataclass(frozen=True)
class PrivilegedActionPolicy:
    action: PrivilegedAction
    required_roles: tuple[str, ...]
    require_step_up: bool
    otp_freshness_seconds: int
    step_up_grace_seconds: int = 60


PRIVILEGED_ACTION_REGISTRY: dict[PrivilegedAction, PrivilegedActionPolicy] = {
    PrivilegedAction.ROLE_CREATE: PrivilegedActionPolicy(
        action=PrivilegedAction.ROLE_CREATE,
        required_roles=("superuser",),
        require_step_up=True,
        otp_freshness_seconds=settings.PRIVILEGED_STEP_UP_TTL_SECONDS,
    ),
    PrivilegedAction.ROLE_PERMISSION_CREATE: PrivilegedActionPolicy(
        action=PrivilegedAction.ROLE_PERMISSION_CREATE,
        required_roles=("superuser",),
        require_step_up=True,
        otp_freshness_seconds=settings.PRIVILEGED_STEP_UP_TTL_SECONDS,
    ),
    PrivilegedAction.ROLE_ASSIGN: PrivilegedActionPolicy(
        action=PrivilegedAction.ROLE_ASSIGN,
        required_roles=("superuser",),
        require_step_up=True,
        otp_freshness_seconds=settings.PRIVILEGED_STEP_UP_TTL_SECONDS,
    ),
    PrivilegedAction.ROLE_REMOVE: PrivilegedActionPolicy(
        action=PrivilegedAction.ROLE_REMOVE,
        required_roles=("superuser",),
        require_step_up=True,
        otp_freshness_seconds=settings.PRIVILEGED_STEP_UP_TTL_SECONDS,
    ),
    PrivilegedAction.ROLE_PERMISSION_ASSIGN: PrivilegedActionPolicy(
        action=PrivilegedAction.ROLE_PERMISSION_ASSIGN,
        required_roles=("superuser",),
        require_step_up=True,
        otp_freshness_seconds=settings.PRIVILEGED_STEP_UP_TTL_SECONDS,
    ),
    PrivilegedAction.ROLE_PERMISSION_REMOVE: PrivilegedActionPolicy(
        action=PrivilegedAction.ROLE_PERMISSION_REMOVE,
        required_roles=("superuser",),
        require_step_up=True,
        otp_freshness_seconds=settings.PRIVILEGED_STEP_UP_TTL_SECONDS,
    ),
    PrivilegedAction.USER_STATUS_EDIT: PrivilegedActionPolicy(
        action=PrivilegedAction.USER_STATUS_EDIT,
        required_roles=("superuser",),
        require_step_up=True,
        otp_freshness_seconds=settings.PRIVILEGED_STEP_UP_TTL_SECONDS,
    ),
    PrivilegedAction.PAYOUT_APPROVE: PrivilegedActionPolicy(
        action=PrivilegedAction.PAYOUT_APPROVE,
        required_roles=("superuser",),
        require_step_up=True,
        otp_freshness_seconds=settings.PRIVILEGED_STEP_UP_TTL_SECONDS,
    ),
    PrivilegedAction.VENDOR_SUSPEND: PrivilegedActionPolicy(
        action=PrivilegedAction.VENDOR_SUSPEND,
        required_roles=("superuser",),
        require_step_up=True,
        otp_freshness_seconds=settings.PRIVILEGED_STEP_UP_TTL_SECONDS,
    ),
    PrivilegedAction.INCIDENT_REVIEW: PrivilegedActionPolicy(
        action=PrivilegedAction.INCIDENT_REVIEW,
        required_roles=("superuser",),
        require_step_up=True,
        otp_freshness_seconds=settings.PRIVILEGED_STEP_UP_TTL_SECONDS,
    ),
    PrivilegedAction.SECURITY_SETTINGS_EDIT: PrivilegedActionPolicy(
        action=PrivilegedAction.SECURITY_SETTINGS_EDIT,
        required_roles=("superuser",),
        require_step_up=True,
        otp_freshness_seconds=settings.PRIVILEGED_STEP_UP_TTL_SECONDS,
    ),
    PrivilegedAction.CONTENT_PROMOTION_PUBLISH: PrivilegedActionPolicy(
        action=PrivilegedAction.CONTENT_PROMOTION_PUBLISH,
        required_roles=("superuser",),
        require_step_up=True,
        otp_freshness_seconds=settings.PRIVILEGED_STEP_UP_TTL_SECONDS,
    ),
}
# Backwards-compatible alias used by legacy tests and callers.
PRIVILEGED_ACTION_POLICY_MAP = PRIVILEGED_ACTION_REGISTRY

_IN_MEMORY_POLICY_OVERRIDES: dict[str, dict[str, Any]] = {}
_IN_MEMORY_STEP_UP_STORE: dict[str, dict[str, Any]] = {}
_IN_MEMORY_STEP_UP_MARKERS: dict[str, dict[str, Any]] = {}


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _policy_override_cache_key(action: PrivilegedAction) -> str:
    return f"privileged:policy:{action.value}"


async def resolve_privileged_action_policy(action: PrivilegedAction) -> PrivilegedActionPolicy:
    default_policy = PRIVILEGED_ACTION_REGISTRY[action]
    override = await RedisCache.get(_policy_override_cache_key(action))
    if override is None:
        override = _IN_MEMORY_POLICY_OVERRIDES.get(_policy_override_cache_key(action))
    if not override:
        return default_policy
    return PrivilegedActionPolicy(
        action=action,
        required_roles=tuple(override.get("required_roles") or list(default_policy.required_roles)),
        require_step_up=bool(override.get("require_step_up", default_policy.require_step_up)),
        otp_freshness_seconds=int(
            override.get("otp_freshness_seconds", settings.PRIVILEGED_STEP_UP_TTL_SECONDS)
        ),
        step_up_grace_seconds=int(override.get("step_up_grace_seconds", settings.PRIVILEGED_STEP_UP_GRACE_SECONDS)),
    )


async def override_privileged_action_policy(
    *,
    action: PrivilegedAction,
    require_step_up: bool | None = None,
    otp_freshness_seconds: int | None = None,
    step_up_grace_seconds: int | None = None,
) -> PrivilegedActionPolicy:
    base_policy = await resolve_privileged_action_policy(action)
    updated = {
        "action": action.value,
        "required_roles": list(base_policy.required_roles),
        "require_step_up": base_policy.require_step_up if require_step_up is None else require_step_up,
        "otp_freshness_seconds": (
            base_policy.otp_freshness_seconds if otp_freshness_seconds is None else otp_freshness_seconds
        ),
        "step_up_grace_seconds": (
            base_policy.step_up_grace_seconds if step_up_grace_seconds is None else step_up_grace_seconds
        ),
    }
    _IN_MEMORY_POLICY_OVERRIDES[_policy_override_cache_key(action)] = updated
    await RedisCache.set(_policy_override_cache_key(action), updated)
    return await resolve_privileged_action_policy(action)


async def list_privileged_action_policies() -> list[PrivilegedActionPolicy]:
    return [await resolve_privileged_action_policy(action) for action in PrivilegedAction]


async def issue_step_up_token(*, user_id: int, action: PrivilegedAction) -> dict[str, Any]:
    policy = await resolve_privileged_action_policy(action)
    token = secrets.token_urlsafe(32)
    marker = secrets.token_urlsafe(18)
    expires_at = _now() + timedelta(seconds=policy.otp_freshness_seconds)
    grace_expires_at = expires_at + timedelta(seconds=policy.step_up_grace_seconds)
    payload = {
        "user_id": user_id,
        "action": action.value,
        "marker": marker,
        "expires_at": expires_at.isoformat(),
        "issued_at": _now().isoformat(),
        "grace_expires_at": grace_expires_at.isoformat(),
    }
    _IN_MEMORY_STEP_UP_STORE[token] = payload
    marker_key = f"{user_id}:{action.value}:{marker}"
    marker_payload = {
        "user_id": user_id,
        "action": action.value,
        "issued_at": payload["issued_at"],
        "expires_at": payload["expires_at"],
        "grace_expires_at": payload["grace_expires_at"],
    }
    _IN_MEMORY_STEP_UP_MARKERS[marker_key] = marker_payload
    await RedisCache.set(
        f"privileged:stepup:{token}",
        payload,
        ttl=policy.otp_freshness_seconds + policy.step_up_grace_seconds,
    )
    await RedisCache.set(
        f"privileged:marker:{marker_key}",
        marker_payload,
        ttl=policy.otp_freshness_seconds + policy.step_up_grace_seconds,
    )
    return {
        "step_up_token": token,
        "expires_at": expires_at.isoformat(),
        "required_freshness_seconds": policy.otp_freshness_seconds,
        "grace_window_seconds": policy.step_up_grace_seconds,
        "action": action.value,
    }


async def _read_step_up_token(*, token: str) -> dict[str, Any] | None:
    payload = await RedisCache.get(f"privileged:stepup:{token}")
    if payload is None:
        payload = _IN_MEMORY_STEP_UP_STORE.get(token)
    return payload


async def _read_step_up_marker(*, user_id: int, action: str, marker: str) -> dict[str, Any] | None:
    marker_key = f"{user_id}:{action}:{marker}"
    payload = await RedisCache.get(f"privileged:marker:{marker_key}")
    if payload is None:
        payload = _IN_MEMORY_STEP_UP_MARKERS.get(marker_key)
    if not payload:
        return None
    try:
        grace_expires_at = datetime.fromisoformat(str(payload.get("grace_expires_at")))
    except Exception:
        grace_expires_at = _now() - timedelta(seconds=1)
    if grace_expires_at <= _now():
        _IN_MEMORY_STEP_UP_MARKERS.pop(marker_key, None)
        await RedisCache.delete(f"privileged:marker:{marker_key}")
        return None
    return payload


async def consume_step_up_token(*, token: str) -> dict[str, Any] | None:
    payload = await _read_step_up_token(token=token)
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
            "grace_window_seconds": policy.step_up_grace_seconds,
            "mode": settings.PRIVILEGED_STEP_UP_MODE,
        },
        "rechallenge": {
            "required": True,
            "reason": reason,
            "retryable": True,
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
            outcome="denied",
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
            outcome="passed",
            request=request,
            metadata={"reason": "step_up_not_required"},
        )
        return
    if settings.PRIVILEGED_STEP_UP_MODE.lower() == "audit":
        await record_privileged_action_audit(
            db,
            actor_user_id=current_user.id,
            action=action.value,
            outcome="bypass_attempt",
            request=request,
            metadata={"reason": "audit_only_mode"},
        )
        return

    token = request.headers.get("X-Privileged-Auth")
    if not token:
        await record_privileged_action_audit(
            db,
            actor_user_id=current_user.id,
            action=action.value,
            outcome="required",
            request=request,
            metadata={"reason": "step_up_required"},
        )
        await db.commit()
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=await build_privileged_action_error(action, reason="step_up_required"),
        )

    payload = await _read_step_up_token(token=token)
    if not payload:
        await record_privileged_action_audit(
            db,
            actor_user_id=current_user.id,
            action=action.value,
            outcome="denied",
            request=request,
            metadata={"reason": "expired_or_invalid_step_up_token"},
        )
        await db.commit()
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=await build_privileged_action_error(action, reason="expired_or_invalid_step_up_token"),
        )
    try:
        expires_at = datetime.fromisoformat(str(payload.get("expires_at")))
    except Exception:
        expires_at = _now() - timedelta(seconds=1)
    if expires_at <= _now():
        await record_privileged_action_audit(
            db,
            actor_user_id=current_user.id,
            action=action.value,
            outcome="denied",
            request=request,
            metadata={"reason": "step_up_expired_requires_rechallenge"},
        )
        await db.commit()
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=await build_privileged_action_error(action, reason="step_up_expired_requires_rechallenge"),
        )
    marker = str(payload.get("marker", "")).strip()
    marker_payload = await _read_step_up_marker(user_id=current_user.id, action=action.value, marker=marker)
    if not marker_payload:
        await record_privileged_action_audit(
            db,
            actor_user_id=current_user.id,
            action=action.value,
            outcome="denied",
            request=request,
            metadata={"reason": "expired_or_invalid_step_up_token", "marker": marker},
        )
        await db.commit()
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=await build_privileged_action_error(action, reason="expired_or_invalid_step_up_token"),
        )
    payload = await consume_step_up_token(token=token)
    if not payload:
        await record_privileged_action_audit(
            db,
            actor_user_id=current_user.id,
            action=action.value,
            outcome="denied",
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
            outcome="denied",
            request=request,
            metadata={"reason": "expired_or_invalid_step_up_token", "subreason": "token_user_mismatch"},
        )
        await db.commit()
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=await build_privileged_action_error(action, reason="expired_or_invalid_step_up_token"),
        )

    if payload.get("action") != action.value:
        await record_privileged_action_audit(
            db,
            actor_user_id=current_user.id,
            action=action.value,
            outcome="denied",
            request=request,
            metadata={"reason": "expired_or_invalid_step_up_token", "subreason": "token_action_mismatch"},
        )
        await db.commit()
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=await build_privileged_action_error(action, reason="expired_or_invalid_step_up_token"),
        )

    await record_privileged_action_audit(
        db,
        actor_user_id=current_user.id,
        action=action.value,
        outcome="passed",
        request=request,
        metadata={
            "reason": "step_up_validated",
            "step_up_issued_at": payload.get("issued_at"),
            "step_up_expires_at": payload.get("expires_at"),
        },
    )

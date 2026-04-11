import pytest

from src.apps.iam.security import (
    PrivilegedAction,
    resolve_privileged_action_policy,
    override_privileged_action_policy,
)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_privileged_policy_override_updates_step_up_requirements():
    original = await resolve_privileged_action_policy(PrivilegedAction.ROLE_ASSIGN)
    assert original.require_step_up is True

    try:
        updated = await override_privileged_action_policy(
            action=PrivilegedAction.ROLE_ASSIGN,
            require_step_up=False,
            otp_freshness_seconds=900,
        )

        assert updated.require_step_up is False
        assert updated.otp_freshness_seconds == 900
    finally:
        await override_privileged_action_policy(
            action=PrivilegedAction.ROLE_ASSIGN,
            require_step_up=original.require_step_up,
            otp_freshness_seconds=original.otp_freshness_seconds,
        )


@pytest.mark.unit
@pytest.mark.asyncio
async def test_privileged_policy_override_is_action_scoped():
    original_assign = await resolve_privileged_action_policy(PrivilegedAction.ROLE_PERMISSION_ASSIGN)
    try:
        await override_privileged_action_policy(
            action=PrivilegedAction.ROLE_PERMISSION_ASSIGN,
            otp_freshness_seconds=420,
        )

        assign_policy = await resolve_privileged_action_policy(PrivilegedAction.ROLE_PERMISSION_ASSIGN)
        remove_policy = await resolve_privileged_action_policy(PrivilegedAction.ROLE_PERMISSION_REMOVE)

        assert assign_policy.otp_freshness_seconds == 420
        assert remove_policy.otp_freshness_seconds != 420
    finally:
        await override_privileged_action_policy(
            action=PrivilegedAction.ROLE_PERMISSION_ASSIGN,
            require_step_up=original_assign.require_step_up,
            otp_freshness_seconds=original_assign.otp_freshness_seconds,
        )

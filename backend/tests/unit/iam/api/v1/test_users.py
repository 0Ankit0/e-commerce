import pytest
import pyotp
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlmodel import select

from src.apps.core import security as core_security
from src.apps.iam import security as iam_security
from src.apps.iam.models.user import User
from src.apps.iam.security import PrivilegedAction, override_privileged_action_policy
from src.apps.iam.utils.hashid import encode_id


async def _make_user(db: AsyncSession, **kwargs) -> User:
    user = User(
        username=kwargs.get("username", "user"),
        email=kwargs.get("email", "user@example.com"),
        hashed_password=core_security.get_password_hash(kwargs.get("password", "TestPass123")),
        is_active=kwargs.get("is_active", True),
        is_superuser=kwargs.get("is_superuser", False),
        is_confirmed=kwargs.get("is_confirmed", True),
        otp_enabled=kwargs.get("otp_enabled", False),
        otp_verified=kwargs.get("otp_verified", False),
        otp_base32=kwargs.get("otp_base32"),
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


async def _login(
    client: AsyncClient,
    username: str,
    password: str = "TestPass123",
    otp_secret: str | None = None,
) -> str:
    response = await client.post(
        "/api/v1/auth/login/?set_cookie=false",
        json={"username": username, "password": password},
    )
    assert response.status_code == 200, response.text
    payload = response.json()
    if payload.get("requires_otp"):
        assert otp_secret is not None, "OTP secret required for OTP-protected login"
        otp_response = await client.post(
            "/api/v1/auth/otp/validate/?set_cookie=false",
            json={"temp_token": payload["temp_token"], "otp_code": pyotp.TOTP(otp_secret).now()},
        )
        assert otp_response.status_code == 200, otp_response.text
        payload = otp_response.json()
    return payload["access"]


@pytest.mark.unit
class TestUserManagementAPI:
    @pytest.mark.asyncio
    async def test_admin_can_update_user_status_and_role(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
    ):
        admin = await _make_user(
            db_session,
            username="adminusers",
            email="adminusers@example.com",
            is_superuser=True,
        )
        target = await _make_user(
            db_session,
            username="manageduser",
            email="managed@example.com",
            is_active=True,
            is_superuser=False,
        )
        target_id = target.id
        token = await _login(client, admin.username)
        original_policy = iam_security.PRIVILEGED_ACTION_POLICY_MAP[PrivilegedAction.USER_STATUS_EDIT]
        await override_privileged_action_policy(action=PrivilegedAction.USER_STATUS_EDIT, require_step_up=False)

        try:
            response = await client.patch(
                f"/api/v1/users/{encode_id(target.id)}",
                headers={"Authorization": f"Bearer {token}"},
                json={
                    "email": "managed-updated@example.com",
                    "first_name": "Managed",
                    "last_name": "User",
                    "phone": "9800000000",
                    "is_active": False,
                    "is_superuser": True,
                },
            )
        finally:
            await override_privileged_action_policy(
                action=PrivilegedAction.USER_STATUS_EDIT,
                require_step_up=original_policy.require_step_up,
                otp_freshness_seconds=original_policy.otp_freshness_seconds,
                step_up_grace_seconds=original_policy.step_up_grace_seconds,
            )

        assert response.status_code == 200, response.text
        data = response.json()
        assert data["email"] == "managed-updated@example.com"
        assert data["first_name"] == "Managed"
        assert data["is_active"] is False
        assert data["is_superuser"] is True

        db_session.expire_all()
        refreshed = await db_session.execute(
            select(User)
            .options(selectinload(User.profile))
            .execution_options(populate_existing=True)
            .where(User.id == target_id)
        )
        user = refreshed.scalars().one()
        assert user.email == "managed-updated@example.com"
        assert user.is_active is False
        assert user.is_superuser is True
        assert user.profile is not None
        assert user.profile.first_name == "Managed"
        assert user.profile.phone == "9800000000"

    @pytest.mark.asyncio
    async def test_admin_list_users_endpoint_returns_paginated_users(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
    ):
        admin = await _make_user(
            db_session,
            username="listadmin",
            email="listadmin@example.com",
            is_superuser=True,
        )
        await _make_user(db_session, username="firstuser", email="first@example.com")
        await _make_user(db_session, username="seconduser", email="second@example.com")
        token = await _login(client, admin.username)

        response = await client.get(
            "/api/v1/users/?skip=0&limit=10&search=user",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200, response.text
        data = response.json()
        assert data["total"] >= 2
        assert len(data["items"]) >= 2

    @pytest.mark.asyncio
    async def test_user_status_edit_requires_step_up_with_machine_reason_codes(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
    ):
        otp_secret = pyotp.random_base32()
        admin = await _make_user(
            db_session,
            username="stepupadmin",
            email="stepupadmin@example.com",
            is_superuser=True,
            otp_enabled=True,
            otp_verified=True,
        )
        admin.otp_base32 = otp_secret
        db_session.add(admin)
        await db_session.commit()
        target = await _make_user(db_session, username="stepuptarget", email="stepuptarget@example.com")
        token = await _login(client, admin.username, otp_secret=otp_secret)
        headers = {"Authorization": f"Bearer {token}"}

        blocked = await client.patch(
            f"/api/v1/users/{encode_id(target.id)}",
            headers=headers,
            json={"is_active": False},
        )
        assert blocked.status_code == 403
        assert blocked.json()["detail"]["reason"] == "step_up_required"

        step_up = await client.post(
            "/api/v1/auth/otp/step-up/verify",
            headers=headers,
            json={"otp_code": pyotp.TOTP(otp_secret).now(), "action": "admin.users.status_edit"},
        )
        assert step_up.status_code == 200

        allowed = await client.patch(
            f"/api/v1/users/{encode_id(target.id)}",
            headers={**headers, "X-Privileged-Auth": step_up.json()["step_up_token"]},
            json={"is_active": False},
        )
        assert allowed.status_code == 200

    @pytest.mark.asyncio
    async def test_user_status_edit_rejects_expired_and_replayed_step_up_tokens(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
    ):
        otp_secret = pyotp.random_base32()
        admin = await _make_user(
            db_session,
            username="stepupexpired",
            email="stepupexpired@example.com",
            is_superuser=True,
            otp_enabled=True,
            otp_verified=True,
        )
        admin.otp_base32 = otp_secret
        db_session.add(admin)
        await db_session.commit()
        target = await _make_user(db_session, username="stepupexp-target", email="stepupexp-target@example.com")
        token = await _login(client, admin.username, otp_secret=otp_secret)
        headers = {"Authorization": f"Bearer {token}"}

        original_policy = iam_security.PRIVILEGED_ACTION_POLICY_MAP[PrivilegedAction.USER_STATUS_EDIT]
        try:
            await override_privileged_action_policy(
                action=PrivilegedAction.USER_STATUS_EDIT,
                otp_freshness_seconds=0,
                step_up_grace_seconds=0,
            )
            expired = await client.post(
                "/api/v1/auth/otp/step-up/verify",
                headers=headers,
                json={"otp_code": pyotp.TOTP(otp_secret).now(), "action": "admin.users.status_edit"},
            )
            assert expired.status_code == 200
            expired_attempt = await client.patch(
                f"/api/v1/users/{encode_id(target.id)}",
                headers={**headers, "X-Privileged-Auth": expired.json()["step_up_token"]},
                json={"is_active": False},
            )
            assert expired_attempt.status_code == 403
            assert expired_attempt.json()["detail"]["reason"] == "step_up_expired_requires_rechallenge"
        finally:
            await override_privileged_action_policy(
                action=PrivilegedAction.USER_STATUS_EDIT,
                require_step_up=original_policy.require_step_up,
                otp_freshness_seconds=original_policy.otp_freshness_seconds,
                step_up_grace_seconds=original_policy.step_up_grace_seconds,
            )

        fresh = await client.post(
            "/api/v1/auth/otp/step-up/verify",
            headers=headers,
            json={"otp_code": pyotp.TOTP(otp_secret).now(), "action": "admin.users.status_edit"},
        )
        assert fresh.status_code == 200
        fresh_token = fresh.json()["step_up_token"]
        allowed = await client.patch(
            f"/api/v1/users/{encode_id(target.id)}",
            headers={**headers, "X-Privileged-Auth": fresh_token},
            json={"is_active": False},
        )
        assert allowed.status_code == 200
        replay = await client.patch(
            f"/api/v1/users/{encode_id(target.id)}",
            headers={**headers, "X-Privileged-Auth": fresh_token},
            json={"is_active": True},
        )
        assert replay.status_code == 403
        assert replay.json()["detail"]["reason"] == "expired_or_invalid_step_up_token"

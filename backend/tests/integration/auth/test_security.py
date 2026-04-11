import asyncio
import time
import pytest
import pyotp
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from src.apps.core import security
from src.apps.core.config import settings
from src.apps.iam.security import PrivilegedAction, PRIVILEGED_ACTION_POLICY_MAP, PrivilegedActionPolicy
from src.apps.iam.models.token_tracking import TokenTracking
from src.apps.iam.models.user import User
from src.apps.observability.models import ObservabilityLogEntry
from src.apps.iam.utils.hashid import encode_id


class TestAuthenticationSecurity:
    """Test authentication security features."""
    
    @pytest.mark.asyncio
    async def test_password_validation(self, client: AsyncClient):
        """Test password strength validation."""
        # Test weak passwords
        weak_passwords = [
            ("short", "Password too short"),
            ("nouppercase123", "Password must contain uppercase"),
            ("NOLOWERCASE123", "Password must contain lowercase"),
            ("NoDigits!", "Password must contain digit"),
        ]
        
        for password, _ in weak_passwords:
            response = await client.post(
                "/api/v1/auth/signup/?set_cookie=false",
                json={
                    "username": "testuser",
                    "email": "test@example.com",
                    "password": password,
                    "confirm_password": password
                }
            )
            assert response.status_code == 422  # Validation error
    
    @pytest.mark.asyncio
    async def test_duplicate_username_prevention(self, client: AsyncClient, db_session: AsyncSession):
        """Test that duplicate usernames are prevented."""
        user_data = {
            "username": "duplicate_test",
            "email": "user1@example.com",
            "password": "SecurePass123",
            "confirm_password": "SecurePass123"
        }
        
        # First signup should succeed
        response1 = await client.post(
            "/api/v1/auth/signup/?set_cookie=false",
            json=user_data
        )
        assert response1.status_code == 200
        
        # Second signup with same username should fail
        user_data["email"] = "user2@example.com"
        response2 = await client.post(
            "/api/v1/auth/signup/?set_cookie=false",
            json=user_data
        )
        assert response2.status_code == 400
        assert "already registered" in response2.json()["detail"].lower()
    
    @pytest.mark.asyncio
    async def test_invalid_token_rejection(self, client: AsyncClient):
        """Test that invalid tokens are rejected."""
        invalid_token = "invalid.token.value"
        headers = {"Authorization": f"Bearer {invalid_token}"}
        
        response = await client.post("/api/v1/auth/logout/", headers=headers)
        assert response.status_code in [401, 403]

    @pytest.mark.asyncio
    async def test_max_login_attempts_lockout(self, client: AsyncClient, db_session: AsyncSession, monkeypatch):
        """Test lockout is enforced after too many failed login attempts."""
        # Reduce the thresholds for speed and determinism
        monkeypatch.setattr("src.apps.core.config.settings.MAX_LOGIN_ATTEMPTS", 2)
        monkeypatch.setattr("src.apps.core.config.settings.ACCOUNT_LOCKOUT_DURATION_MINUTES", 5)
        
        user_data = {
            "username": "lockout_user",
            "email": "lockout@example.com",
            "password": "ValidPass123",
            "confirm_password": "ValidPass123"
        }
        await client.post("/api/v1/auth/signup/?set_cookie=false", json=user_data)

        # Two failed attempts should be accepted (still under the limit)
        for _ in range(2):
            response = await client.post(
                "/api/v1/auth/login/?set_cookie=false",
                json={"username": "lockout_user", "password": "WrongPass"}
            )
            assert response.status_code == 400

        # Third attempt should be blocked by lockout
        response = await client.post(
            "/api/v1/auth/login/?set_cookie=false",
            json={"username": "lockout_user", "password": "WrongPass"}
        )
        assert response.status_code == 429
        assert "too many login attempts" in response.json().get("detail", "").lower()

    @pytest.mark.asyncio
    async def test_require_email_verification_before_login(self, client: AsyncClient, db_session: AsyncSession, monkeypatch):
        """Test login is blocked when email verification is required and user is unconfirmed."""
        monkeypatch.setattr("src.apps.core.config.settings.REQUIRE_EMAIL_VERIFICATION", True)

        user_data = {
            "username": "verify_user",
            "email": "verify@example.com",
            "password": "ValidPass123",
            "confirm_password": "ValidPass123"
        }
        await client.post("/api/v1/auth/signup/?set_cookie=false", json=user_data)

        # Should be blocked until user is confirmed
        response = await client.post(
            "/api/v1/auth/login/?set_cookie=false",
            json={"username": "verify_user", "password": "ValidPass123"}
        )
        assert response.status_code == 403

        # Confirm the user in DB and attempt login again
        result = await db_session.execute(select(User).where(User.username == "verify_user"))
        user = result.scalars().first()
        assert user is not None
        user.is_confirmed = True
        await db_session.commit()

        response = await client.post(
            "/api/v1/auth/login/?set_cookie=false",
            json={"username": "verify_user", "password": "ValidPass123"}
        )
        assert response.status_code == 200
        assert "access" in response.json()

    @pytest.mark.asyncio
    async def test_lockout_threshold_boundary_blocks_on_next_attempt(self, client: AsyncClient, monkeypatch):
        monkeypatch.setattr("src.apps.core.config.settings.MAX_LOGIN_ATTEMPTS", 3)
        monkeypatch.setattr("src.apps.core.config.settings.ACCOUNT_LOCKOUT_DURATION_MINUTES", 5)

        await client.post(
            "/api/v1/auth/signup/?set_cookie=false",
            json={
                "username": "lockout_boundary",
                "email": "lockout-boundary@example.com",
                "password": "ValidPass123",
                "confirm_password": "ValidPass123",
            },
        )

        for _ in range(3):
            bad_login = await client.post(
                "/api/v1/auth/login/?set_cookie=false",
                json={"username": "lockout_boundary", "password": "WrongPass"},
            )
            assert bad_login.status_code == 400

        blocked = await client.post(
            "/api/v1/auth/login/?set_cookie=false",
            json={"username": "lockout_boundary", "password": "WrongPass"},
        )
        assert blocked.status_code == 429

    @pytest.mark.asyncio
    async def test_role_change_during_active_session_revokes_privileged_access(self, client: AsyncClient, db_session: AsyncSession):
        admin = User(
            username="active_session_admin",
            email="active-session-admin@example.com",
            hashed_password=security.get_password_hash("ValidPass123"),
            is_active=True,
            is_superuser=True,
            is_confirmed=True,
        )
        db_session.add(admin)
        await db_session.commit()

        login_resp = await client.post(
            "/api/v1/auth/login/?set_cookie=false",
            json={"username": "active_session_admin", "password": "ValidPass123"},
        )
        token = login_resp.json()["access"]
        headers = {"Authorization": f"Bearer {token}"}

        allowed = await client.get("/api/v1/users/", headers=headers)
        assert allowed.status_code == 200

        db_admin = (await db_session.execute(select(User).where(User.username == "active_session_admin"))).scalars().one()
        db_admin.is_superuser = False
        await db_session.commit()

        forbidden = await client.get("/api/v1/users/", headers=headers)
        assert forbidden.status_code == 403

    @pytest.mark.asyncio
    async def test_disabled_user_token_is_rejected(self, client: AsyncClient, db_session: AsyncSession):
        user = User(
            username="disabled_token_user",
            email="disabled-token@example.com",
            hashed_password=security.get_password_hash("ValidPass123"),
            is_active=True,
            is_superuser=False,
            is_confirmed=True,
        )
        db_session.add(user)
        await db_session.commit()

        login_resp = await client.post(
            "/api/v1/auth/login/?set_cookie=false",
            json={"username": "disabled_token_user", "password": "ValidPass123"},
        )
        token = login_resp.json()["access"]

        db_user = (await db_session.execute(select(User).where(User.username == "disabled_token_user"))).scalars().one()
        db_user.is_active = False
        await db_session.commit()

        me_resp = await client.get("/api/v1/users/me", headers={"Authorization": f"Bearer {token}"})
        assert me_resp.status_code == 400
        assert "inactive" in me_resp.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_token_churn_spike_keeps_only_latest_ip_tokens_active(self, client: AsyncClient, db_session: AsyncSession):
        username = "token_churn_user"
        await client.post(
            "/api/v1/auth/signup/?set_cookie=false",
            json={
                "username": username,
                "email": "token-churn@example.com",
                "password": "ValidPass123",
                "confirm_password": "ValidPass123",
            },
        )

        for _ in range(6):
            login_resp = await client.post(
                "/api/v1/auth/login/?set_cookie=false",
                json={"username": username, "password": "ValidPass123"},
            )
            if login_resp.status_code == 429:
                await asyncio.sleep(1)
                login_resp = await client.post(
                    "/api/v1/auth/login/?set_cookie=false",
                    json={"username": username, "password": "ValidPass123"},
                )
            assert login_resp.status_code == 200, login_resp.text

        db_user = (await db_session.execute(select(User).where(User.username == username))).scalars().one()
        tokens = (await db_session.execute(select(TokenTracking).where(TokenTracking.user_id == db_user.id))).scalars().all()
        active_tokens = [token for token in tokens if token.is_active]
        assert len(active_tokens) == 2
        assert len(tokens) >= 12

    @pytest.mark.asyncio
    async def test_privileged_action_requires_recent_otp_and_blocks_replay(self, client: AsyncClient, db_session: AsyncSession):
        otp_secret = pyotp.random_base32()
        admin = User(
            username="stepup_admin",
            email="stepup-admin@example.com",
            hashed_password=security.get_password_hash("ValidPass123"),
            is_active=True,
            is_superuser=True,
            is_confirmed=True,
            otp_enabled=True,
            otp_verified=True,
            otp_base32=otp_secret,
        )
        target = User(
            username="stepup_target",
            email="stepup-target@example.com",
            hashed_password=security.get_password_hash("ValidPass123"),
            is_active=True,
            is_superuser=False,
            is_confirmed=True,
        )
        db_session.add(admin)
        db_session.add(target)
        await db_session.commit()

        login = await client.post(
            "/api/v1/auth/login/?set_cookie=false",
            json={"username": "stepup_admin", "password": "ValidPass123"},
        )
        token = login.json()["access"]
        headers = {"Authorization": f"Bearer {token}"}

        blocked = await client.patch(
            f"/api/v1/users/{encode_id(target.id)}",
            json={"is_active": False},
            headers=headers,
        )
        assert blocked.status_code == 403
        assert blocked.json()["detail"]["code"] == "OTP_CHALLENGE_REQUIRED"

        step_up = await client.post(
            "/api/v1/auth/otp/step-up/verify",
            json={"otp_code": pyotp.TOTP(otp_secret).now(), "action": PrivilegedAction.USER_STATUS_EDIT.value},
            headers=headers,
        )
        assert step_up.status_code == 200, step_up.text
        step_token = step_up.json()["step_up_token"]

        allowed_headers = {**headers, "X-Privileged-Auth": step_token}
        allowed = await client.patch(
            f"/api/v1/users/{encode_id(target.id)}",
            json={"is_active": False},
            headers=allowed_headers,
        )
        assert allowed.status_code == 200, allowed.text
        assert allowed.json()["is_active"] is False

        replay = await client.patch(
            f"/api/v1/users/{encode_id(target.id)}",
            json={"is_active": True},
            headers=allowed_headers,
        )
        assert replay.status_code == 403
        assert replay.json()["detail"]["code"] == "OTP_CHALLENGE_REQUIRED"



    @pytest.mark.asyncio
    async def test_privileged_action_audits_challenge_success_and_replay(self, client: AsyncClient, db_session: AsyncSession):
        otp_secret = pyotp.random_base32()
        admin = User(
            username="stepup_audit_admin",
            email="stepup-audit-admin@example.com",
            hashed_password=security.get_password_hash("ValidPass123"),
            is_active=True,
            is_superuser=True,
            is_confirmed=True,
            otp_enabled=True,
            otp_verified=True,
            otp_base32=otp_secret,
        )
        target = User(
            username="stepup_audit_target",
            email="stepup-audit-target@example.com",
            hashed_password=security.get_password_hash("ValidPass123"),
            is_active=True,
            is_superuser=False,
            is_confirmed=True,
        )
        db_session.add(admin)
        db_session.add(target)
        await db_session.commit()

        login = await client.post(
            "/api/v1/auth/login/?set_cookie=false",
            json={"username": "stepup_audit_admin", "password": "ValidPass123"},
        )
        headers = {"Authorization": f"Bearer {login.json()['access']}"}

        await client.patch(
            f"/api/v1/users/{encode_id(target.id)}",
            json={"is_active": False},
            headers=headers,
        )

        step_up = await client.post(
            "/api/v1/auth/otp/step-up/verify",
            json={"otp_code": pyotp.TOTP(otp_secret).now(), "action": PrivilegedAction.USER_STATUS_EDIT.value},
            headers=headers,
        )
        step_token = step_up.json()["step_up_token"]

        await client.patch(
            f"/api/v1/users/{encode_id(target.id)}",
            json={"is_active": False},
            headers={**headers, "X-Privileged-Auth": step_token},
        )

        await client.patch(
            f"/api/v1/users/{encode_id(target.id)}",
            json={"is_active": True},
            headers={**headers, "X-Privileged-Auth": step_token},
        )

        audit_rows = (
            await db_session.execute(
                select(ObservabilityLogEntry)
                .where(
                    ObservabilityLogEntry.user_id == admin.id,
                    ObservabilityLogEntry.event_code.in_(
                        [
                            "admin.privileged_action.challenge_required",
                            "admin.privileged_action.success",
                        ]
                    ),
                )
                .order_by(ObservabilityLogEntry.timestamp.asc())
            )
        ).scalars().all()

        outcomes = [row.event_code for row in audit_rows]
        assert "admin.privileged_action.success" in outcomes
        assert outcomes.count("admin.privileged_action.challenge_required") >= 2

        replay_challenge = next(
            row
            for row in reversed(audit_rows)
            if row.event_code == "admin.privileged_action.challenge_required"
        )
        assert replay_challenge.metadata_json["reason"] == "expired_or_invalid_step_up_token"

    @pytest.mark.asyncio
    async def test_privileged_action_role_change_mid_session_is_audited_failure(self, client: AsyncClient, db_session: AsyncSession):
        otp_secret = pyotp.random_base32()
        admin = User(
            username="stepup_rolechange_admin",
            email="stepup-rolechange-admin@example.com",
            hashed_password=security.get_password_hash("ValidPass123"),
            is_active=True,
            is_superuser=True,
            is_confirmed=True,
            otp_enabled=True,
            otp_verified=True,
            otp_base32=otp_secret,
        )
        target = User(
            username="stepup_rolechange_target",
            email="stepup-rolechange-target@example.com",
            hashed_password=security.get_password_hash("ValidPass123"),
            is_active=True,
            is_superuser=False,
            is_confirmed=True,
        )
        db_session.add(admin)
        db_session.add(target)
        await db_session.commit()

        login = await client.post(
            "/api/v1/auth/login/?set_cookie=false",
            json={"username": "stepup_rolechange_admin", "password": "ValidPass123"},
        )
        headers = {"Authorization": f"Bearer {login.json()['access']}"}

        step_up = await client.post(
            "/api/v1/auth/otp/step-up/verify",
            json={"otp_code": pyotp.TOTP(otp_secret).now(), "action": PrivilegedAction.USER_STATUS_EDIT.value},
            headers=headers,
        )

        admin.is_superuser = False
        await db_session.commit()

        forbidden = await client.patch(
            f"/api/v1/users/{encode_id(target.id)}",
            json={"is_active": False},
            headers={**headers, "X-Privileged-Auth": step_up.json()["step_up_token"]},
        )
        assert forbidden.status_code == 403

        failure_audit = (
            await db_session.execute(
                select(ObservabilityLogEntry)
                .where(
                    ObservabilityLogEntry.user_id == admin.id,
                    ObservabilityLogEntry.event_code == "admin.privileged_action.failure",
                )
                .order_by(ObservabilityLogEntry.timestamp.desc())
            )
        ).scalars().first()

        assert failure_audit is not None
        assert failure_audit.metadata_json["reason"] == "role_requirement_not_met"

    @pytest.mark.asyncio
    async def test_privileged_action_rejects_expired_step_up_session(self, client: AsyncClient, db_session: AsyncSession, monkeypatch):
        otp_secret = pyotp.random_base32()
        admin = User(
            username="stepup_expiry_admin",
            email="stepup-expiry-admin@example.com",
            hashed_password=security.get_password_hash("ValidPass123"),
            is_active=True,
            is_superuser=True,
            is_confirmed=True,
            otp_enabled=True,
            otp_verified=True,
            otp_base32=otp_secret,
        )
        target = User(
            username="stepup_expiry_target",
            email="stepup-expiry-target@example.com",
            hashed_password=security.get_password_hash("ValidPass123"),
            is_active=True,
            is_superuser=False,
            is_confirmed=True,
        )
        db_session.add(admin)
        db_session.add(target)
        await db_session.commit()

        original_policy = PRIVILEGED_ACTION_POLICY_MAP[PrivilegedAction.USER_STATUS_EDIT]
        monkeypatch.setitem(
            PRIVILEGED_ACTION_POLICY_MAP,
            PrivilegedAction.USER_STATUS_EDIT,
            PrivilegedActionPolicy(
                action=original_policy.action,
                required_roles=original_policy.required_roles,
                require_step_up=original_policy.require_step_up,
                otp_freshness_seconds=1,
                step_up_grace_seconds=1,
            ),
        )

        login = await client.post(
            "/api/v1/auth/login/?set_cookie=false",
            json={"username": "stepup_expiry_admin", "password": "ValidPass123"},
        )
        token = login.json()["access"]
        headers = {"Authorization": f"Bearer {token}"}
        step_up = await client.post(
            "/api/v1/auth/otp/step-up/verify",
            json={"otp_code": pyotp.TOTP(otp_secret).now(), "action": PrivilegedAction.USER_STATUS_EDIT.value},
            headers=headers,
        )
        assert step_up.status_code == 200
        time.sleep(2)

        expired = await client.patch(
            f"/api/v1/users/{encode_id(target.id)}",
            json={"is_active": False},
            headers={**headers, "X-Privileged-Auth": step_up.json()["step_up_token"]},
        )
        assert expired.status_code == 403
        assert expired.json()["detail"]["code"] == "OTP_CHALLENGE_REQUIRED"
        assert expired.json()["detail"]["reason"] == "step_up_expired_requires_rechallenge"

    @pytest.mark.asyncio
    async def test_privileged_action_audit_only_mode_records_bypass(self, client: AsyncClient, db_session: AsyncSession, monkeypatch):
        admin = User(
            username="stepup_audit_only_admin",
            email="stepup-audit-only-admin@example.com",
            hashed_password=security.get_password_hash("ValidPass123"),
            is_active=True,
            is_superuser=True,
            is_confirmed=True,
            otp_enabled=False,
            otp_verified=False,
        )
        target = User(
            username="stepup_audit_only_target",
            email="stepup-audit-only-target@example.com",
            hashed_password=security.get_password_hash("ValidPass123"),
            is_active=True,
            is_superuser=False,
            is_confirmed=True,
        )
        db_session.add(admin)
        db_session.add(target)
        await db_session.commit()

        monkeypatch.setattr(settings, "PRIVILEGED_STEP_UP_MODE", "audit")

        login = await client.post(
            "/api/v1/auth/login/?set_cookie=false",
            json={"username": "stepup_audit_only_admin", "password": "ValidPass123"},
        )
        headers = {"Authorization": f"Bearer {login.json()['access']}"}
        allowed = await client.patch(
            f"/api/v1/users/{encode_id(target.id)}",
            json={"is_active": False},
            headers=headers,
        )
        assert allowed.status_code == 200

        bypass_event = (
            await db_session.execute(
                select(ObservabilityLogEntry)
                .where(
                    ObservabilityLogEntry.user_id == admin.id,
                    ObservabilityLogEntry.event_code == "admin.privileged_action.bypassed",
                )
                .order_by(ObservabilityLogEntry.timestamp.desc())
            )
        ).scalars().first()
        assert bypass_event is not None

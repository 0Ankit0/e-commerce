import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from src.apps.core import security
from tests.factories import UserFactory


async def _make_user(db: AsyncSession, **kwargs):
    defaults = dict(
        username="quotaadmin",
        email="quotaadmin@example.com",
        hashed_password=security.get_password_hash("TestPass123"),
        is_active=True,
        is_confirmed=True,
    )
    defaults.update(kwargs)
    user = UserFactory.build(**defaults)
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


async def _login(client: AsyncClient, username: str, password: str = "TestPass123") -> str:
    resp = await client.post("/api/v1/auth/login/?set_cookie=false", json={"username": username, "password": password})
    assert resp.status_code == 200
    return resp.json()["access"]


@pytest.mark.asyncio
async def test_admin_can_update_quota_config_and_read_dashboard(client: AsyncClient, db_session: AsyncSession) -> None:
    await _make_user(db_session, is_superuser=True)
    token = await _login(client, "quotaadmin")

    update = await client.put(
        "/api/v1/notifications/admin/sms-quotas/config/",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "provider": "default",
            "per_user_daily_limit": 2,
            "per_ip_window_limit": 3,
            "ip_window_seconds": 120,
            "per_device_window_limit": 2,
            "device_window_seconds": 60,
            "global_provider_daily_limit": 20,
            "hard_throttle_action": "cooldown",
            "hard_cooldown_seconds": 180,
            "trusted_entry_points": ["otp_validate"],
            "privileged_override_enabled": True,
        },
    )
    assert update.status_code == 200, update.text
    assert update.json()["per_user_daily_limit"] == 2
    assert update.json()["hard_throttle_action"] == "cooldown"

    dashboard = await client.get(
        "/api/v1/notifications/admin/sms-quotas/dashboard/",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert dashboard.status_code == 200
    assert "totals" in dashboard.json()
    assert "blocked_attempts" in dashboard.json()["totals"]

    audit = await client.get(
        "/api/v1/notifications/admin/sms-quotas/audit/",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert audit.status_code == 200
    assert audit.json()["count"] >= 1

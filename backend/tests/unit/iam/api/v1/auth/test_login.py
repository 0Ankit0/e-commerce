import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from src.apps.core import security
from src.apps.observability.models import ObservabilityLogEntry
from tests.factories import UserFactory


class TestLogin:
    """Test login endpoint."""
    
    @pytest.mark.asyncio
    async def test_login_success(self, client: AsyncClient, db_session: AsyncSession):
        """Test successful login."""
        # Create user with whitelisted IP
        hashed_pw = security.get_password_hash("TestPass123")
        user = UserFactory.build(
            username="loginuser",
            email="login@example.com",
            hashed_password=hashed_pw,
            is_active=True
        )
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)
        
        login_data = {
            "username": "loginuser",
            "password": "TestPass123"
        }
        
        response = await client.post(
            "/api/v1/auth/login/?set_cookie=false",
            json=login_data
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "access" in data
        assert "refresh" in data
    
    @pytest.mark.asyncio
    async def test_login_wrong_password(self, client: AsyncClient, db_session: AsyncSession):
        """Test login with wrong password."""
        hashed_pw = security.get_password_hash("TestPass123")
        user = UserFactory.build(
            username="wrongpwuser",
            hashed_password=hashed_pw
        )
        db_session.add(user)
        await db_session.commit()
        
        login_data = {
            "username": "wrongpwuser",
            "password": "WrongPass456"
        }
        
        response = await client.post(
            "/api/v1/auth/login/?set_cookie=false",
            json=login_data
        )
        
        assert response.status_code == 400
        assert "Incorrect username or password" in response.json()["detail"]
    
    @pytest.mark.asyncio
    async def test_login_nonexistent_user(self, client: AsyncClient):
        """Test login with non-existent user."""
        login_data = {
            "username": "nonexistent",
            "password": "TestPass123"
        }
        
        response = await client.post(
            "/api/v1/auth/login/?set_cookie=false",
            json=login_data
        )
        
        assert response.status_code == 400
        assert "Incorrect username or password" in response.json()["detail"]
    
    @pytest.mark.asyncio
    async def test_login_inactive_user(self, client: AsyncClient, db_session: AsyncSession):
        """Test login with inactive user."""
        hashed_pw = security.get_password_hash("TestPass123")
        user = UserFactory.build(
            username="inactiveuser",
            hashed_password=hashed_pw,
            is_active=False
        )
        db_session.add(user)
        await db_session.commit()
        
        login_data = {
            "username": "inactiveuser",
            "password": "TestPass123"
        }
        
        response = await client.post(
            "/api/v1/auth/login/?set_cookie=false",
            json=login_data
        )
        
        assert response.status_code == 400
        assert "Inactive user" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_admin_login_recommends_otp_when_not_enabled(self, client: AsyncClient, db_session: AsyncSession):
        hashed_pw = security.get_password_hash("TestPass123")
        admin = UserFactory.build(
            username="adminloginuser",
            email="adminlogin@example.com",
            hashed_password=hashed_pw,
            is_active=True,
            is_superuser=True,
            is_confirmed=True,
        )
        db_session.add(admin)
        await db_session.commit()

        response = await client.post(
            "/api/v1/auth/login/?set_cookie=false",
            json={"username": "adminloginuser", "password": "TestPass123"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["otp_recommended"] is True
        assert "access" in data

    @pytest.mark.asyncio
    async def test_admin_otp_status_endpoint_lists_admin_accounts(self, client: AsyncClient, db_session: AsyncSession):
        hashed_pw = security.get_password_hash("TestPass123")
        admin = UserFactory.build(
            username="otpstatusadmin",
            email="otpstatus@example.com",
            hashed_password=hashed_pw,
            is_active=True,
            is_superuser=True,
            is_confirmed=True,
        )
        db_session.add(admin)
        await db_session.commit()
        await db_session.refresh(admin)

        login_resp = await client.post(
            "/api/v1/auth/login/?set_cookie=false",
            json={"username": "otpstatusadmin", "password": "TestPass123"},
        )
        token = login_resp.json()["access"]
        headers = {"Authorization": f"Bearer {token}"}

        enable_resp = await client.post("/api/v1/auth/otp/enable/", headers=headers)
        assert enable_resp.status_code == 200, enable_resp.text
        audit_logs = (
            await db_session.execute(
                select(ObservabilityLogEntry).where(ObservabilityLogEntry.user_id == admin.id)
            )
        ).scalars().all()
        assert any(log.event_code == "auth.admin_otp.setup_started" for log in audit_logs)

        status_resp = await client.get("/api/v1/auth/admin/security/admin-otp-status", headers=headers)
        assert status_resp.status_code == 200, status_resp.text
        item = status_resp.json()["items"][0]
        assert item["username"] == "otpstatusadmin"
        assert item["last_verified_state"] == "pending_verification"

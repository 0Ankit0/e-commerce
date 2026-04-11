import pytest
from fastapi import HTTPException
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from src.apps.iam.models.user import User
from src.apps.core import security
from src.apps.vendors.models import Vendor, VendorKYCStatus, VendorStatus
from src.apps.vendors.services import assert_vendor_status_transition, mark_vendor_kyc_status


class TestCompleteUserFlow:
    """Test complete user authentication flow."""
    
    @pytest.mark.asyncio
    async def test_signup_and_login_flow(self, client: AsyncClient, db_session: AsyncSession):
        """Test complete signup and login flow."""
        # Step 1: Signup
        signup_data = {
            "username": "flowuser",
            "email": "flow@example.com",
            "password": "FlowPass123",
            "confirm_password": "FlowPass123",
            "first_name": "Flow",
            "last_name": "User"
        }
        
        signup_response = await client.post(
            "/api/v1/auth/signup/?set_cookie=false",
            json=signup_data
        )
        
        assert signup_response.status_code == 200
        signup_data_response = signup_response.json()
        assert "access" in signup_data_response
        assert "refresh" in signup_data_response
        
        # Step 2: Verify user exists in database
        result = await db_session.execute(
            select(User).where(User.username == "flowuser")
        )
        user = result.scalars().first()
        assert user is not None
        assert user.email == "flow@example.com"
        
        # Step 3: Login with the same credentials
        login_data = {
            "username": "flowuser",
            "password": "FlowPass123"
        }
        
        login_response = await client.post(
            "/api/v1/auth/login/?set_cookie=false",
            json=login_data
        )
        
        assert login_response.status_code == 200
        login_data_response = login_response.json()
        assert "access" in login_data_response
        assert "refresh" in login_data_response
    
    @pytest.mark.asyncio
    async def test_token_refresh_flow(self, client: AsyncClient, db_session: AsyncSession):
        """Test token refresh flow."""
        # Create and login user
        hashed_pw = security.get_password_hash("TestPass123")
        user = User(
            username="refreshflowuser",
            email="refreshflow@example.com",
            hashed_password=hashed_pw,
            is_active=True
        )
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)
        
        # Login to get tokens
        login_response = await client.post(
            "/api/v1/auth/login/?set_cookie=false",
            json={"username": "refreshflowuser", "password": "TestPass123"}
        )
        
        assert login_response.status_code == 200
        tokens = login_response.json()
        refresh_token = tokens["refresh"]
        
        # Refresh the token
        refresh_response = await client.post(
            "/api/v1/auth/refresh/?set_cookie=false",
            json={"refresh_token": refresh_token}
        )
        
        assert refresh_response.status_code == 200
        new_tokens = refresh_response.json()
        assert "access" in new_tokens
        assert "refresh" in new_tokens
        assert new_tokens["access"] != tokens["access"]
        assert new_tokens["refresh"] != tokens["refresh"]

    @pytest.mark.asyncio
    async def test_vendor_kyc_lifecycle_and_resubmission_loop(self, db_session: AsyncSession):
        vendor = Vendor(
            tenant_id=1,
            owner_user_id=1,
            business_name="Loop Vendor",
            display_name="Loop",
            slug="loop-vendor",
            status=VendorStatus.PENDING,
        )
        db_session.add(vendor)
        await db_session.commit()
        await db_session.refresh(vendor)

        assert vendor.kyc_status == VendorKYCStatus.SUBMITTED
        assert_vendor_status_transition(vendor, VendorStatus.UNDER_REVIEW)
        vendor.status = VendorStatus.UNDER_REVIEW
        mark_vendor_kyc_status(vendor, kyc_status=VendorKYCStatus.UNDER_REVIEW, reviewer_user_id=99)
        mark_vendor_kyc_status(vendor, kyc_status=VendorKYCStatus.RESUBMISSION_REQUIRED, reviewer_user_id=99, reason="PAN blurry")
        mark_vendor_kyc_status(vendor, kyc_status=VendorKYCStatus.UNDER_REVIEW, reviewer_user_id=99)
        mark_vendor_kyc_status(vendor, kyc_status=VendorKYCStatus.APPROVED, reviewer_user_id=99)
        await db_session.commit()
        await db_session.refresh(vendor)

        assert vendor.kyc_status == VendorKYCStatus.APPROVED
        assert vendor.kyc_review_started_at is not None
        assert vendor.kyc_reviewed_at is not None
        assert "PAN blurry" in vendor.kyc_review_reasons_json

    def test_vendor_invalid_transition_blocked(self):
        vendor = Vendor(
            tenant_id=1,
            owner_user_id=1,
            business_name="Invalid Transition Vendor",
            display_name="Invalid",
            slug="invalid-transition-vendor",
            status=VendorStatus.PENDING,
        )
        with pytest.raises(HTTPException):
            assert_vendor_status_transition(vendor, VendorStatus.APPROVED)

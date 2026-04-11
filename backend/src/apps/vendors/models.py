from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Optional

from sqlmodel import Field, SQLModel

from src.apps.core.time import utc_now


class VendorStatus(str, Enum):
    PENDING = "pending"
    NEEDS_RESUBMISSION = "needs_resubmission"
    UNDER_REVIEW = "under_review"
    APPROVED = "approved"
    REJECTED = "rejected"
    SUSPENDED = "suspended"


class VendorKYCStatus(str, Enum):
    SUBMITTED = "submitted"
    UNDER_REVIEW = "under_review"
    RESUBMISSION_REQUIRED = "resubmission_required"
    APPROVED = "approved"
    REJECTED = "rejected"
    SUSPENDED_AFTER_APPROVAL = "suspended_after_approval"


class CommissionTier(str, Enum):
    STANDARD = "standard"
    PREMIUM = "premium"
    ENTERPRISE = "enterprise"


class VendorDocumentStatus(str, Enum):
    SUBMITTED = "submitted"
    UNDER_REVIEW = "under_review"
    NEEDS_RESUBMISSION = "needs_resubmission"
    VERIFIED = "verified"
    REJECTED = "rejected"


class BankAccountVerificationStatus(str, Enum):
    PENDING = "pending"
    VERIFIED = "verified"
    FAILED = "failed"


class Vendor(SQLModel, table=True):
    __tablename__ = "vendors"  # type: ignore[assignment]

    id: Optional[int] = Field(default=None, primary_key=True)
    tenant_id: int = Field(foreign_key="tenant.id", index=True)
    owner_user_id: int = Field(foreign_key="user.id", index=True)
    business_name: str = Field(max_length=255)
    display_name: str = Field(max_length=255)
    slug: str = Field(index=True, unique=True, max_length=120)
    description: str = Field(default="", max_length=2000)
    logo_url: str = Field(default="", max_length=500)
    banner_url: str = Field(default="", max_length=500)
    gstin: str = Field(default="", max_length=80)
    pan: str = Field(default="", max_length=80)
    status: VendorStatus = Field(default=VendorStatus.PENDING)
    commission_tier: CommissionTier = Field(default=CommissionTier.STANDARD)
    rating: float = Field(default=0.0, ge=0, le=5)
    rating_count: int = Field(default=0, ge=0)
    product_count: int = Field(default=0, ge=0)
    onboarding_step: str = Field(default="profile_submitted", max_length=80)
    kyc_status: VendorKYCStatus = Field(default=VendorKYCStatus.SUBMITTED, index=True)
    kyc_submitted_at: datetime = Field(default_factory=utc_now)
    kyc_review_started_at: Optional[datetime] = Field(default=None)
    kyc_reviewed_at: Optional[datetime] = Field(default=None)
    kyc_last_reviewer_user_id: Optional[int] = Field(default=None, foreign_key="user.id", index=True)
    kyc_assigned_reviewer_user_id: Optional[int] = Field(default=None, foreign_key="user.id", index=True)
    kyc_reviewer_assigned_at: Optional[datetime] = Field(default=None)
    kyc_review_reasons_json: str = Field(default="[]")
    verification_timeline_json: str = Field(default="[]")
    approved_at: Optional[datetime] = Field(default=None)
    rejected_reason: str = Field(default="", max_length=500)
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


class VendorDocument(SQLModel, table=True):
    __tablename__ = "vendor_documents"  # type: ignore[assignment]

    id: Optional[int] = Field(default=None, primary_key=True)
    vendor_id: int = Field(foreign_key="vendors.id", index=True)
    doc_type: str = Field(max_length=50)
    doc_number: str = Field(default="", max_length=120)
    file_url: str = Field(default="", max_length=500)
    status: VendorDocumentStatus = Field(default=VendorDocumentStatus.SUBMITTED)
    remarks: str = Field(default="", max_length=500)
    version: int = Field(default=1, ge=1)
    is_current: bool = Field(default=True, index=True)
    uploaded_at: datetime = Field(default_factory=utc_now)
    verified_at: Optional[datetime] = Field(default=None)
    reviewed_by_user_id: Optional[int] = Field(default=None, foreign_key="user.id", index=True)
    resubmission_requested_at: Optional[datetime] = Field(default=None)
    review_reason_history_json: str = Field(default="[]")


class BankAccount(SQLModel, table=True):
    __tablename__ = "vendor_bank_accounts"  # type: ignore[assignment]

    id: Optional[int] = Field(default=None, primary_key=True)
    vendor_id: int = Field(foreign_key="vendors.id", index=True)
    account_name: str = Field(max_length=255)
    account_number: str = Field(max_length=80)
    ifsc_code: str = Field(default="", max_length=50)
    bank_name: str = Field(default="", max_length=255)
    is_primary: bool = Field(default=True)
    verification_status: BankAccountVerificationStatus = Field(
        default=BankAccountVerificationStatus.PENDING
    )
    remarks: str = Field(default="", max_length=500)
    created_at: datetime = Field(default_factory=utc_now)


class Warehouse(SQLModel, table=True):
    __tablename__ = "warehouses"  # type: ignore[assignment]

    id: Optional[int] = Field(default=None, primary_key=True)
    vendor_id: int = Field(foreign_key="vendors.id", index=True)
    name: str = Field(max_length=255)
    address: str = Field(default="", max_length=500)
    city: str = Field(default="", max_length=120)
    state: str = Field(default="", max_length=120)
    pincode: str = Field(default="", max_length=20)
    contact_phone: str = Field(default="", max_length=20)
    latitude: Optional[float] = Field(default=None)
    longitude: Optional[float] = Field(default=None)
    is_default: bool = Field(default=False)
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=utc_now)


class VendorPayoutStatus(str, Enum):
    REQUESTED = "requested"
    PENDING = "pending"
    PROCESSING = "processing"
    PAID = "paid"
    FAILED = "failed"


class VendorPayout(SQLModel, table=True):
    __tablename__ = "vendor_payouts"  # type: ignore[assignment]

    id: Optional[int] = Field(default=None, primary_key=True)
    vendor_id: int = Field(foreign_key="vendors.id", index=True)
    amount: float = Field(default=0, ge=0)
    commission_amount: float = Field(default=0, ge=0)
    period_start: Optional[datetime] = Field(default=None)
    period_end: Optional[datetime] = Field(default=None)
    status: VendorPayoutStatus = Field(default=VendorPayoutStatus.PENDING)
    reference: str = Field(default="", max_length=120)
    payout_batch_id: Optional[int] = Field(default=None, foreign_key="vendor_payout_batches.id", index=True)
    created_at: datetime = Field(default_factory=utc_now)
    paid_at: Optional[datetime] = Field(default=None)


class VendorTimelineEvent(SQLModel, table=True):
    __tablename__ = "vendor_timeline_events"  # type: ignore[assignment]

    id: Optional[int] = Field(default=None, primary_key=True)
    vendor_id: int = Field(foreign_key="vendors.id", index=True)
    actor_user_id: Optional[int] = Field(default=None, foreign_key="user.id", index=True)
    event_type: str = Field(max_length=80, index=True)
    message: str = Field(default="", max_length=500)
    payload_json: str = Field(default="{}")
    created_at: datetime = Field(default_factory=utc_now)


class VendorPayoutRequest(SQLModel, table=True):
    __tablename__ = "vendor_payout_requests"  # type: ignore[assignment]

    id: Optional[int] = Field(default=None, primary_key=True)
    vendor_id: int = Field(foreign_key="vendors.id", index=True)
    requested_by_user_id: int = Field(foreign_key="user.id", index=True)
    amount: float = Field(default=0, ge=0)
    currency: str = Field(default="NPR", max_length=3)
    notes: str = Field(default="", max_length=500)
    status: VendorPayoutStatus = Field(default=VendorPayoutStatus.REQUESTED)
    created_at: datetime = Field(default_factory=utc_now)
    reviewed_at: Optional[datetime] = Field(default=None)


class VendorPayoutBatch(SQLModel, table=True):
    __tablename__ = "vendor_payout_batches"  # type: ignore[assignment]

    id: Optional[int] = Field(default=None, primary_key=True)
    code: str = Field(max_length=80, unique=True, index=True)
    status: VendorPayoutStatus = Field(default=VendorPayoutStatus.PENDING)
    total_amount: float = Field(default=0, ge=0)
    item_count: int = Field(default=0, ge=0)
    settlement_export_url: str = Field(default="", max_length=500)
    notes: str = Field(default="", max_length=500)
    created_at: datetime = Field(default_factory=utc_now)
    processed_at: Optional[datetime] = Field(default=None)

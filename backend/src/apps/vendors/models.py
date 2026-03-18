from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Optional

from sqlmodel import Field, SQLModel


class VendorStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    SUSPENDED = "suspended"


class CommissionTier(str, Enum):
    STANDARD = "standard"
    PREMIUM = "premium"
    ENTERPRISE = "enterprise"


class VendorDocumentStatus(str, Enum):
    PENDING = "pending"
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
    approved_at: Optional[datetime] = Field(default=None)
    rejected_reason: str = Field(default="", max_length=500)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class VendorDocument(SQLModel, table=True):
    __tablename__ = "vendor_documents"  # type: ignore[assignment]

    id: Optional[int] = Field(default=None, primary_key=True)
    vendor_id: int = Field(foreign_key="vendors.id", index=True)
    doc_type: str = Field(max_length=50)
    doc_number: str = Field(default="", max_length=120)
    file_url: str = Field(default="", max_length=500)
    status: VendorDocumentStatus = Field(default=VendorDocumentStatus.PENDING)
    remarks: str = Field(default="", max_length=500)
    uploaded_at: datetime = Field(default_factory=datetime.utcnow)
    verified_at: Optional[datetime] = Field(default=None)


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
    created_at: datetime = Field(default_factory=datetime.utcnow)


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
    created_at: datetime = Field(default_factory=datetime.utcnow)


class VendorPayoutStatus(str, Enum):
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
    created_at: datetime = Field(default_factory=datetime.utcnow)
    paid_at: Optional[datetime] = Field(default=None)

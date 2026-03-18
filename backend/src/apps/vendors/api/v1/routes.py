from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select, func

from src.apps.analytics.dependencies import get_analytics
from src.apps.analytics.service import AnalyticsService
from src.apps.iam.api.deps import get_current_active_superuser, get_current_user, get_db
from src.apps.iam.models.user import User
from src.apps.iam.utils.hashid import decode_id_or_404
from src.apps.orders.models import VendorOrder
from src.apps.vendors.models import (
    BankAccount,
    BankAccountVerificationStatus,
    CommissionTier,
    Vendor,
    VendorDocument,
    VendorDocumentStatus,
    VendorPayout,
    VendorPayoutStatus,
    VendorStatus,
    Warehouse,
)
from src.apps.vendors.services import (
    ensure_vendor_active,
    get_vendor_for_user,
    get_vendor_or_404,
    mark_vendor_status,
    require_tenant_admin,
    serialize_vendor,
)

router = APIRouter()


class VendorCreateRequest(BaseModel):
    tenant_id: str
    business_name: str = Field(min_length=2, max_length=255)
    display_name: str = Field(min_length=2, max_length=255)
    slug: str = Field(min_length=2, max_length=120)
    description: str = ""
    gstin: str = ""
    pan: str = ""


class VendorDecisionRequest(BaseModel):
    reason: str = ""


class WarehouseCreateRequest(BaseModel):
    name: str
    address: str = ""
    city: str = ""
    state: str = ""
    pincode: str = ""
    contact_phone: str = ""
    is_default: bool = False


class VendorDocumentCreateRequest(BaseModel):
    doc_type: str
    doc_number: str = ""
    file_url: str = ""


class BankAccountCreateRequest(BaseModel):
    account_name: str
    account_number: str
    ifsc_code: str = ""
    bank_name: str = ""


class VendorStatusUpdateRequest(BaseModel):
    reason: str = ""


@router.post("/vendor/profile", status_code=status.HTTP_201_CREATED)
async def create_vendor_profile(
    payload: VendorCreateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    analytics: AnalyticsService = Depends(get_analytics),
):
    tenant = await require_tenant_admin(decode_id_or_404(payload.tenant_id), current_user, db)
    existing = (await db.execute(select(Vendor).where(Vendor.tenant_id == tenant.id))).scalars().first()
    if existing:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Vendor already exists for tenant")
    slug_exists = (await db.execute(select(Vendor).where(Vendor.slug == payload.slug))).scalars().first()
    if slug_exists:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Vendor slug already exists")

    vendor = Vendor(
        tenant_id=tenant.id,
        owner_user_id=current_user.id,
        business_name=payload.business_name,
        display_name=payload.display_name,
        slug=payload.slug,
        description=payload.description,
        gstin=payload.gstin,
        pan=payload.pan,
    )
    db.add(vendor)
    await db.commit()
    await db.refresh(vendor)

    await analytics.capture(
        str(current_user.id),
        "vendor_profile_created",
        {"vendor_id": vendor.id, "tenant_id": vendor.tenant_id},
    )
    return {"vendor": serialize_vendor(vendor)}


@router.get("/vendor/profile")
async def get_my_vendor_profile(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    vendor = await get_vendor_for_user(current_user, db)
    warehouses = (
        await db.execute(select(Warehouse).where(Warehouse.vendor_id == vendor.id).order_by(Warehouse.id.asc()))
    ).scalars().all()
    documents = (
        await db.execute(select(VendorDocument).where(VendorDocument.vendor_id == vendor.id).order_by(VendorDocument.id.desc()))
    ).scalars().all()
    bank_accounts = (
        await db.execute(select(BankAccount).where(BankAccount.vendor_id == vendor.id).order_by(BankAccount.id.desc()))
    ).scalars().all()
    return {
        "vendor": serialize_vendor(vendor),
        "warehouses": [
            {
                "id": encode_id(warehouse.id),
                "name": warehouse.name,
                "city": warehouse.city,
                "state": warehouse.state,
                "pincode": warehouse.pincode,
                "is_default": warehouse.is_default,
            }
            for warehouse in warehouses
        ],
        "documents": [
            {
                "id": encode_id(document.id),
                "doc_type": document.doc_type,
                "doc_number": document.doc_number,
                "file_url": document.file_url,
                "status": document.status.value,
            }
            for document in documents
        ],
        "bank_accounts": [
            {
                "id": encode_id(bank.id),
                "account_name": bank.account_name,
                "bank_name": bank.bank_name,
                "verification_status": bank.verification_status.value,
                "is_primary": bank.is_primary,
            }
            for bank in bank_accounts
        ],
    }


@router.post("/vendor/warehouses", status_code=status.HTTP_201_CREATED)
async def create_vendor_warehouse(
    payload: WarehouseCreateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    vendor = await get_vendor_for_user(current_user, db)
    ensure_vendor_active(vendor)
    warehouse = Warehouse(vendor_id=vendor.id, **payload.model_dump())
    db.add(warehouse)
    await db.commit()
    await db.refresh(warehouse)
    return {"warehouse": {"id": encode_id(warehouse.id), **payload.model_dump()}}


@router.post("/vendor/documents", status_code=status.HTTP_201_CREATED)
async def upload_vendor_document(
    payload: VendorDocumentCreateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    vendor = await get_vendor_for_user(current_user, db)
    document = VendorDocument(vendor_id=vendor.id, **payload.model_dump())
    db.add(document)
    await db.commit()
    await db.refresh(document)
    return {"document_id": encode_id(document.id)}


@router.post("/vendor/bank-accounts", status_code=status.HTTP_201_CREATED)
async def create_bank_account(
    payload: BankAccountCreateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    vendor = await get_vendor_for_user(current_user, db)
    bank = BankAccount(vendor_id=vendor.id, **payload.model_dump())
    db.add(bank)
    await db.commit()
    await db.refresh(bank)
    return {"bank_account_id": encode_id(bank.id)}


@router.get("/vendor/analytics")
async def vendor_analytics(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    vendor = await get_vendor_for_user(current_user, db)
    order_count = (
        await db.execute(select(func.count()).select_from(VendorOrder).where(VendorOrder.vendor_id == vendor.id))
    ).one()[0]
    total_revenue = (
        await db.execute(select(func.coalesce(func.sum(VendorOrder.vendor_amount), 0)).where(VendorOrder.vendor_id == vendor.id))
    ).one()[0]
    return {
        "vendor": serialize_vendor(vendor),
        "analytics": {
            "orders": order_count,
            "net_revenue": round(float(total_revenue or 0), 2),
            "product_count": vendor.product_count,
            "rating": vendor.rating,
        },
    }


@router.get("/vendor/payouts")
async def list_vendor_payouts(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    vendor = await get_vendor_for_user(current_user, db)
    payouts = (
        await db.execute(select(VendorPayout).where(VendorPayout.vendor_id == vendor.id).order_by(VendorPayout.created_at.desc()))
    ).scalars().all()
    return {
        "items": [
            {
                "id": encode_id(payout.id),
                "amount": payout.amount,
                "commission_amount": payout.commission_amount,
                "status": payout.status.value,
                "reference": payout.reference,
                "created_at": payout.created_at.isoformat(),
            }
            for payout in payouts
        ],
        "total": len(payouts),
    }


@router.get("/admin/vendors")
async def list_vendors(
    _: User = Depends(get_current_active_superuser),
    db: AsyncSession = Depends(get_db),
):
    vendors = (await db.execute(select(Vendor).order_by(Vendor.created_at.desc()))).scalars().all()
    return {"items": [serialize_vendor(vendor) for vendor in vendors], "total": len(vendors)}


@router.post("/admin/vendors/{vendor_id}/approve")
async def approve_vendor(
    vendor_id: str,
    _: User = Depends(get_current_active_superuser),
    db: AsyncSession = Depends(get_db),
):
    vendor = await get_vendor_or_404(decode_id_or_404(vendor_id), db)
    mark_vendor_status(vendor, VendorStatus.APPROVED)
    await db.commit()
    await db.refresh(vendor)
    return {"vendor": serialize_vendor(vendor)}


@router.post("/admin/vendors/{vendor_id}/reject")
async def reject_vendor(
    vendor_id: str,
    payload: VendorDecisionRequest,
    _: User = Depends(get_current_active_superuser),
    db: AsyncSession = Depends(get_db),
):
    vendor = await get_vendor_or_404(decode_id_or_404(vendor_id), db)
    mark_vendor_status(vendor, VendorStatus.REJECTED, payload.reason)
    await db.commit()
    await db.refresh(vendor)
    return {"vendor": serialize_vendor(vendor)}


@router.post("/admin/vendors/{vendor_id}/suspend")
async def suspend_vendor(
    vendor_id: str,
    payload: VendorStatusUpdateRequest,
    _: User = Depends(get_current_active_superuser),
    db: AsyncSession = Depends(get_db),
):
    vendor = await get_vendor_or_404(decode_id_or_404(vendor_id), db)
    mark_vendor_status(vendor, VendorStatus.SUSPENDED, payload.reason)
    await db.commit()
    await db.refresh(vendor)
    return {"vendor": serialize_vendor(vendor)}


@router.post("/admin/vendor-documents/{document_id}/verify")
async def verify_vendor_document(
    document_id: str,
    _: User = Depends(get_current_active_superuser),
    db: AsyncSession = Depends(get_db),
):
    document = await db.get(VendorDocument, decode_id_or_404(document_id))
    if document is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vendor document not found")
    document.status = VendorDocumentStatus.VERIFIED
    document.verified_at = datetime.utcnow()
    await db.commit()
    return {"success": True}


@router.post("/admin/vendor-bank-accounts/{bank_account_id}/verify")
async def verify_vendor_bank_account(
    bank_account_id: str,
    _: User = Depends(get_current_active_superuser),
    db: AsyncSession = Depends(get_db),
):
    bank_account = await db.get(BankAccount, decode_id_or_404(bank_account_id))
    if bank_account is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bank account not found")
    bank_account.verification_status = BankAccountVerificationStatus.VERIFIED
    await db.commit()
    return {"success": True}


@router.post("/admin/vendor-payouts/{vendor_id}/create")
async def create_vendor_payout(
    vendor_id: str,
    _: User = Depends(get_current_active_superuser),
    db: AsyncSession = Depends(get_db),
):
    decoded_vendor_id = decode_id_or_404(vendor_id)
    vendor = await db.get(Vendor, decoded_vendor_id)
    if vendor is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vendor not found")
    vendor_orders = (
        await db.execute(select(VendorOrder).where(VendorOrder.vendor_id == decoded_vendor_id))
    ).scalars().all()
    net_amount = round(sum(vendor_order.vendor_amount for vendor_order in vendor_orders if vendor_order.status.value == "delivered"), 2)
    commission_amount = round(sum(vendor_order.commission for vendor_order in vendor_orders if vendor_order.status.value == "delivered"), 2)
    payout = VendorPayout(
        vendor_id=decoded_vendor_id,
        amount=net_amount,
        commission_amount=commission_amount,
        status=VendorPayoutStatus.PENDING,
        reference=f"PO-{decoded_vendor_id}-{int(datetime.utcnow().timestamp())}",
    )
    db.add(payout)
    await db.commit()
    await db.refresh(payout)
    return {"payout_id": encode_id(payout.id)}


def encode_id(value: int | None) -> str | None:
    if value is None:
        return None
    from src.apps.iam.utils.hashid import encode_id as _encode_id

    return _encode_id(value)

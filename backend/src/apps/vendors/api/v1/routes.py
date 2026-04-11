from __future__ import annotations

import csv
import io
import json

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select, func

from src.apps.analytics.dependencies import get_analytics
from src.apps.analytics.service import AnalyticsService
from src.apps.core.time import utc_now
from src.apps.iam.api.deps import get_current_active_superuser, get_current_user, get_db
from src.apps.iam.models.user import User
from src.apps.iam.utils.hashid import decode_id_or_404, encode_id
from src.apps.notification.services.commerce_events import notify_payout_event
from src.apps.orders.models import VendorOrder
from src.apps.vendors.models import (
    BankAccount,
    BankAccountVerificationStatus,
    CommissionTier,
    Vendor,
    VendorDocument,
    VendorDocumentStatus,
    VendorKYCStatus,
    VendorPayout,
    VendorPayoutBatch,
    VendorPayoutRequest,
    VendorPayoutStatus,
    VendorStatus,
    VendorTimelineEvent,
    Warehouse,
)
from src.apps.vendors.services import (
    append_document_review_history,
    assert_document_status_transition,
    assert_vendor_status_transition,
    ensure_vendor_kyc_ready_for_approval,
    ensure_vendor_active,
    get_vendor_for_user,
    get_vendor_or_404,
    mark_vendor_kyc_status,
    mark_vendor_status,
    record_vendor_timeline_event,
    require_tenant_admin,
    serialize_vendor,
    serialize_vendor_kyc_timeline,
    serialize_vendor_payout,
    serialize_vendor_payout_request,
    validate_vendor_kyc_requirements,
)
from src.apps.iam.security import PrivilegedAction, enforce_privileged_action

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
    reason: str = Field(min_length=1, max_length=500)


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


class VendorDocumentUpsertRequest(VendorDocumentCreateRequest):
    pass


class BankAccountCreateRequest(BaseModel):
    account_name: str
    account_number: str
    ifsc_code: str = ""
    bank_name: str = ""


class VendorStatusUpdateRequest(BaseModel):
    reason: str = ""


class VendorDocumentReviewRequest(BaseModel):
    remarks: str = Field(default="", max_length=500)
    expected_uploaded_at: str = Field(min_length=1)
    expected_version: int = Field(gt=0)


class VendorDocumentDecisionRequest(VendorDocumentReviewRequest):
    remarks: str = Field(min_length=1, max_length=500)


class PayoutRequestCreateRequest(BaseModel):
    amount: float = Field(gt=0)
    notes: str = ""


class PayoutBatchCreateRequest(BaseModel):
    payout_request_ids: list[str] = Field(default_factory=list)
    notes: str = ""


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
    await record_vendor_timeline_event(
        vendor=vendor,
        event_type="vendor.profile_created",
        message="Vendor profile submitted for review",
        actor_user_id=current_user.id,
        payload={"tenant_id": vendor.tenant_id},
        db=db,
    )
    await db.commit()

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
        await db.execute(
            select(VendorDocument)
            .where(VendorDocument.vendor_id == vendor.id)
            .order_by(VendorDocument.doc_type.asc(), VendorDocument.version.desc(), VendorDocument.id.desc())
        )
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
                "remarks": document.remarks,
                "version": document.version,
                "is_current": document.is_current,
                "uploaded_at": document.uploaded_at.isoformat(),
                "review_reason_history": json.loads(document.review_reason_history_json or "[]"),
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
                "remarks": bank.remarks,
            }
            for bank in bank_accounts
        ],
        "timeline": [
            {
                "id": encode_id(event.id or 0),
                "event_type": event.event_type,
                "message": event.message,
                "created_at": event.created_at.isoformat(),
                "payload": json.loads(event.payload_json or "{}"),
            }
            for event in (
                await db.execute(
                    select(VendorTimelineEvent).where(VendorTimelineEvent.vendor_id == vendor.id).order_by(VendorTimelineEvent.created_at.desc())
                )
            ).scalars().all()
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
    payload: VendorDocumentUpsertRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    vendor = await get_vendor_for_user(current_user, db)
    repeated_upload = False
    latest_document = (
        await db.execute(
            select(VendorDocument)
            .where(
                VendorDocument.vendor_id == vendor.id,
                VendorDocument.doc_type == payload.doc_type,
                VendorDocument.is_current == True,  # noqa: E712
            )
            .order_by(VendorDocument.version.desc(), VendorDocument.id.desc())
        )
    ).scalars().first()
    if latest_document and latest_document.doc_number == payload.doc_number and latest_document.file_url == payload.file_url:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Duplicate upload detected for current document version",
        )

    if latest_document:
        repeated_upload = True
        latest_document.is_current = False
        document = VendorDocument(
            vendor_id=vendor.id,
            doc_type=payload.doc_type,
            doc_number=payload.doc_number,
            file_url=payload.file_url,
            status=VendorDocumentStatus.SUBMITTED,
            version=latest_document.version + 1,
            is_current=True,
        )
        db.add(document)
    else:
        document = VendorDocument(vendor_id=vendor.id, **payload.model_dump(), status=VendorDocumentStatus.SUBMITTED)
        db.add(document)
    append_document_review_history(
        document,
        status_value=VendorDocumentStatus.SUBMITTED,
        note="Document submitted by vendor",
        actor_user_id=current_user.id,
    )
    await db.commit()
    await db.refresh(document)
    await record_vendor_timeline_event(
        vendor=vendor,
        event_type="vendor.document_reuploaded" if repeated_upload else "vendor.document_uploaded",
        message=f"Document uploaded: {document.doc_type}",
        actor_user_id=current_user.id,
        payload={"document_id": document.id, "doc_type": document.doc_type, "repeated_upload": repeated_upload},
        db=db,
    )
    await db.commit()
    return {"document_id": encode_id(document.id)}


@router.put("/vendor/documents/{doc_type}")
async def upsert_vendor_document(
    doc_type: str,
    payload: VendorDocumentUpsertRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    payload.doc_type = doc_type.strip().lower()
    return await upload_vendor_document(payload=payload, current_user=current_user, db=db)


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
    await record_vendor_timeline_event(
        vendor=vendor,
        event_type="vendor.bank_account_added",
        message="Bank account submitted for verification",
        actor_user_id=current_user.id,
        payload={"bank_account_id": bank.id},
        db=db,
    )
    await db.commit()
    return {"bank_account_id": encode_id(bank.id)}


@router.post("/vendor/documents/{document_id}/resubmit")
async def resubmit_vendor_document(
    document_id: str,
    payload: VendorDocumentCreateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    vendor = await get_vendor_for_user(current_user, db)
    document = await db.get(VendorDocument, decode_id_or_404(document_id))
    if document is None or document.vendor_id != vendor.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vendor document not found")
    if not document.is_current:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Only current document version can be resubmitted")
    if payload.doc_type != document.doc_type:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Document type cannot change on resubmission")
    if document.status not in {VendorDocumentStatus.NEEDS_RESUBMISSION, VendorDocumentStatus.REJECTED}:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Document is not eligible for resubmission")
    if document.doc_number == payload.doc_number and document.file_url == payload.file_url:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Duplicate upload detected for current document version")

    document.is_current = False
    assert_document_status_transition(document.status, VendorDocumentStatus.SUBMITTED)
    new_document = VendorDocument(
        vendor_id=vendor.id,
        doc_type=document.doc_type,
        doc_number=payload.doc_number,
        file_url=payload.file_url,
        status=VendorDocumentStatus.SUBMITTED,
        version=document.version + 1,
        is_current=True,
        review_reason_history_json=document.review_reason_history_json,
    )
    db.add(new_document)
    append_document_review_history(
        new_document,
        status_value=VendorDocumentStatus.SUBMITTED,
        note="Document resubmitted by vendor",
        actor_user_id=current_user.id,
    )
    await record_vendor_timeline_event(
        vendor=vendor,
        event_type="vendor.document_resubmitted",
        message=f"Document resubmitted: {document.doc_type}",
        actor_user_id=current_user.id,
        payload={"previous_document_id": document.id, "new_version": document.version + 1},
        db=db,
    )
    await db.commit()
    await db.refresh(new_document)
    return {"success": True, "document_id": encode_id(new_document.id)}


@router.post("/vendor/bank-accounts/{bank_account_id}/resubmit")
async def resubmit_bank_account(
    bank_account_id: str,
    payload: BankAccountCreateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    vendor = await get_vendor_for_user(current_user, db)
    bank = await db.get(BankAccount, decode_id_or_404(bank_account_id))
    if bank is None or bank.vendor_id != vendor.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bank account not found")
    bank.account_name = payload.account_name
    bank.account_number = payload.account_number
    bank.ifsc_code = payload.ifsc_code
    bank.bank_name = payload.bank_name
    bank.verification_status = BankAccountVerificationStatus.PENDING
    bank.remarks = ""
    await record_vendor_timeline_event(
        vendor=vendor,
        event_type="vendor.bank_account_resubmitted",
        message="Bank account resubmitted for verification",
        actor_user_id=current_user.id,
        payload={"bank_account_id": bank.id},
        db=db,
    )
    await db.commit()
    return {"success": True}


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
    return {"items": [serialize_vendor_payout(payout) for payout in payouts], "total": len(payouts)}


@router.get("/vendor/timeline")
async def list_vendor_timeline(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    vendor = await get_vendor_for_user(current_user, db)
    events = (
        await db.execute(
            select(VendorTimelineEvent).where(VendorTimelineEvent.vendor_id == vendor.id).order_by(VendorTimelineEvent.created_at.desc())
        )
    ).scalars().all()
    return {
        "items": [
            {
                "id": encode_id(event.id or 0),
                "event_type": event.event_type,
                "message": event.message,
                "created_at": event.created_at.isoformat(),
                "payload": json.loads(event.payload_json or "{}"),
            }
            for event in events
        ],
        "total": len(events),
    }


@router.post("/vendor/payout-requests", status_code=status.HTTP_201_CREATED)
async def create_payout_request(
    payload: PayoutRequestCreateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    vendor = await get_vendor_for_user(current_user, db)
    request = VendorPayoutRequest(
        vendor_id=vendor.id,
        requested_by_user_id=current_user.id,
        amount=payload.amount,
        notes=payload.notes,
    )
    db.add(request)
    await record_vendor_timeline_event(
        vendor=vendor,
        event_type="vendor.payout_requested",
        message="Vendor requested payout",
        actor_user_id=current_user.id,
        payload={"amount": payload.amount},
        db=db,
    )
    await db.commit()
    await db.refresh(request)
    await notify_payout_event(
        db=db,
        user_id=vendor.owner_user_id,
        vendor_id=encode_id(vendor.id),
        event="vendor.payout_requested",
        title="Payout request submitted",
        body="Your payout request has been submitted for review.",
        amount=request.amount,
        payout_request_id=encode_id(request.id),
        status=request.status.value,
    )
    return {"payout_request": serialize_vendor_payout_request(request)}


@router.get("/vendor/payout-requests")
async def list_vendor_payout_requests(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    vendor = await get_vendor_for_user(current_user, db)
    requests = (
        await db.execute(
            select(VendorPayoutRequest).where(VendorPayoutRequest.vendor_id == vendor.id).order_by(VendorPayoutRequest.created_at.desc())
        )
    ).scalars().all()
    return {"items": [serialize_vendor_payout_request(request) for request in requests], "total": len(requests)}


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
    admin_user: User = Depends(get_current_active_superuser),
    db: AsyncSession = Depends(get_db),
):
    vendor = await get_vendor_or_404(decode_id_or_404(vendor_id), db)
    assert_vendor_status_transition(vendor, VendorStatus.APPROVED)
    mark_vendor_status(vendor, VendorStatus.APPROVED)
    mark_vendor_kyc_status(vendor, kyc_status=VendorKYCStatus.APPROVED, reviewer_user_id=admin_user.id)
    await record_vendor_timeline_event(
        vendor=vendor,
        event_type="vendor.approved",
        message="Vendor approved",
        actor_user_id=admin_user.id,
        db=db,
    )
    await db.commit()
    await db.refresh(vendor)
    return {"vendor": serialize_vendor(vendor)}


@router.post("/admin/vendors/{vendor_id}/reject")
async def reject_vendor(
    vendor_id: str,
    payload: VendorDecisionRequest,
    admin_user: User = Depends(get_current_active_superuser),
    db: AsyncSession = Depends(get_db),
):
    vendor = await get_vendor_or_404(decode_id_or_404(vendor_id), db)
    assert_vendor_status_transition(vendor, VendorStatus.REJECTED)
    mark_vendor_status(vendor, VendorStatus.REJECTED, payload.reason)
    mark_vendor_kyc_status(vendor, kyc_status=VendorKYCStatus.REJECTED, reviewer_user_id=admin_user.id, reason=payload.reason)
    await record_vendor_timeline_event(
        vendor=vendor,
        event_type="vendor.rejected",
        message="Vendor rejected",
        payload={"reason": payload.reason},
        actor_user_id=admin_user.id,
        db=db,
    )
    await db.commit()
    await db.refresh(vendor)
    return {"vendor": serialize_vendor(vendor)}


@router.post("/admin/vendors/{vendor_id}/suspend")
async def suspend_vendor(
    vendor_id: str,
    payload: VendorStatusUpdateRequest,
    request: Request,
    admin_user: User = Depends(get_current_active_superuser),
    db: AsyncSession = Depends(get_db),
):
    await enforce_privileged_action(
        db=db,
        request=request,
        current_user=admin_user,
        action=PrivilegedAction.USER_STATUS_EDIT,
    )
    vendor = await get_vendor_or_404(decode_id_or_404(vendor_id), db)
    assert_vendor_status_transition(vendor, VendorStatus.SUSPENDED)
    mark_vendor_status(vendor, VendorStatus.SUSPENDED, payload.reason)
    await record_vendor_timeline_event(
        vendor=vendor,
        event_type="vendor.suspended",
        message="Vendor suspended",
        payload={"reason": payload.reason},
        actor_user_id=admin_user.id,
        db=db,
    )
    await db.commit()
    await db.refresh(vendor)
    return {"vendor": serialize_vendor(vendor)}


@router.post("/admin/vendors/{vendor_id}/mark-under-review")
async def mark_vendor_under_review(
    vendor_id: str,
    admin_user: User = Depends(get_current_active_superuser),
    db: AsyncSession = Depends(get_db),
):
    vendor = await get_vendor_or_404(decode_id_or_404(vendor_id), db)
    assert_vendor_status_transition(vendor, VendorStatus.UNDER_REVIEW)
    mark_vendor_status(vendor, VendorStatus.UNDER_REVIEW)
    mark_vendor_kyc_status(vendor, kyc_status=VendorKYCStatus.UNDER_REVIEW, reviewer_user_id=admin_user.id)
    await record_vendor_timeline_event(
        vendor=vendor,
        event_type="vendor.under_review",
        message="Vendor moved to under review",
        actor_user_id=admin_user.id,
        db=db,
    )
    await db.commit()
    return {"vendor": serialize_vendor(vendor)}


@router.post("/admin/vendors/{vendor_id}/request-resubmission")
async def request_vendor_resubmission(
    vendor_id: str,
    payload: VendorDecisionRequest,
    admin_user: User = Depends(get_current_active_superuser),
    db: AsyncSession = Depends(get_db),
):
    vendor = await get_vendor_or_404(decode_id_or_404(vendor_id), db)
    assert_vendor_status_transition(vendor, VendorStatus.NEEDS_RESUBMISSION)
    mark_vendor_status(vendor, VendorStatus.NEEDS_RESUBMISSION, payload.reason)
    mark_vendor_kyc_status(
        vendor,
        kyc_status=VendorKYCStatus.RESUBMISSION_REQUIRED,
        reviewer_user_id=admin_user.id,
        reason=payload.reason,
    )
    await record_vendor_timeline_event(
        vendor=vendor,
        event_type="vendor.resubmission_requested",
        message="Vendor asked to resubmit verification details",
        payload={"reason": payload.reason},
        actor_user_id=admin_user.id,
        db=db,
    )
    await db.commit()
    return {"vendor": serialize_vendor(vendor)}


@router.post("/admin/vendors/{vendor_id}/kyc/approve")
async def approve_vendor_kyc(
    vendor_id: str,
    admin_user: User = Depends(get_current_active_superuser),
    db: AsyncSession = Depends(get_db),
):
    vendor = await get_vendor_or_404(decode_id_or_404(vendor_id), db)
    await ensure_vendor_kyc_ready_for_approval(vendor, db)
    mark_vendor_kyc_status(vendor, kyc_status=VendorKYCStatus.APPROVED, reviewer_user_id=admin_user.id)
    await record_vendor_timeline_event(
        vendor=vendor,
        event_type="vendor.kyc_approved",
        message="KYC approved",
        actor_user_id=admin_user.id,
        db=db,
    )
    await db.commit()
    return {"success": True, "kyc_status": vendor.kyc_status.value}


@router.post("/admin/vendor-documents/{document_id}/mark-under-review")
async def mark_vendor_document_under_review(
    document_id: str,
    payload: VendorDocumentReviewRequest,
    admin_user: User = Depends(get_current_active_superuser),
    db: AsyncSession = Depends(get_db),
):
    document = await db.get(VendorDocument, decode_id_or_404(document_id))
    if document is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vendor document not found")
    if not document.is_current:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Cannot review non-current document version")
    if document.uploaded_at.isoformat() != payload.expected_uploaded_at:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Stale document review action")
    if document.version != payload.expected_version:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Stale document version for review action")
    if document.status != VendorDocumentStatus.SUBMITTED:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Document is not submitted")
    assert_document_status_transition(document.status, VendorDocumentStatus.UNDER_REVIEW)
    document.status = VendorDocumentStatus.UNDER_REVIEW
    document.remarks = payload.remarks
    append_document_review_history(document, status_value=VendorDocumentStatus.UNDER_REVIEW, note=payload.remarks or "Document moved to under review", actor_user_id=admin_user.id)
    vendor = await db.get(Vendor, document.vendor_id)
    if vendor:
        await record_vendor_timeline_event(
            vendor=vendor,
            event_type="vendor.document_under_review",
            message=f"Document under review: {document.doc_type}",
            payload={"document_id": document.id},
            actor_user_id=admin_user.id,
            db=db,
        )
    await db.commit()
    return {"success": True}


@router.post("/admin/vendor-documents/{document_id}/verify")
async def verify_vendor_document(
    document_id: str,
    payload: VendorDocumentReviewRequest,
    admin_user: User = Depends(get_current_active_superuser),
    db: AsyncSession = Depends(get_db),
):
    document = await db.get(VendorDocument, decode_id_or_404(document_id))
    if document is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vendor document not found")
    if not document.is_current:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Cannot review non-current document version")
    if document.uploaded_at.isoformat() != payload.expected_uploaded_at:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Stale document review action")
    if document.version != payload.expected_version:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Stale document version for review action")
    if document.status != VendorDocumentStatus.UNDER_REVIEW:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Document is not under review")
    assert_document_status_transition(document.status, VendorDocumentStatus.VERIFIED)
    document.status = VendorDocumentStatus.VERIFIED
    document.remarks = payload.remarks
    document.verified_at = utc_now()
    document.reviewed_by_user_id = admin_user.id
    append_document_review_history(document, status_value=VendorDocumentStatus.VERIFIED, note=payload.remarks or "Document verified", actor_user_id=admin_user.id)
    vendor = await db.get(Vendor, document.vendor_id)
    if vendor:
        await record_vendor_timeline_event(
            vendor=vendor,
            event_type="vendor.document_verified",
            message=f"Document verified: {document.doc_type}",
            payload={"document_id": document.id},
            actor_user_id=admin_user.id,
            db=db,
        )
    await db.commit()
    return {"success": True}


@router.post("/admin/vendor-documents/{document_id}/reject")
async def reject_vendor_document(
    document_id: str,
    payload: VendorDocumentDecisionRequest,
    admin_user: User = Depends(get_current_active_superuser),
    db: AsyncSession = Depends(get_db),
):
    document = await db.get(VendorDocument, decode_id_or_404(document_id))
    if document is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vendor document not found")
    if not document.is_current:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Cannot review non-current document version")
    if document.uploaded_at.isoformat() != payload.expected_uploaded_at:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Stale document review action")
    if document.version != payload.expected_version:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Stale document version for review action")
    if document.status != VendorDocumentStatus.UNDER_REVIEW:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Document is not under review")
    assert_document_status_transition(document.status, VendorDocumentStatus.REJECTED)
    document.status = VendorDocumentStatus.REJECTED
    document.remarks = payload.remarks
    document.reviewed_by_user_id = admin_user.id
    append_document_review_history(document, status_value=VendorDocumentStatus.REJECTED, note=payload.remarks, actor_user_id=admin_user.id)
    vendor = await db.get(Vendor, document.vendor_id)
    if vendor:
        mark_vendor_status(vendor, VendorStatus.NEEDS_RESUBMISSION, payload.remarks)
        mark_vendor_kyc_status(vendor, kyc_status=VendorKYCStatus.RESUBMISSION_REQUIRED, reviewer_user_id=admin_user.id, reason=payload.remarks)
        await record_vendor_timeline_event(
            vendor=vendor,
            event_type="vendor.document_rejected",
            message=f"Document rejected: {document.doc_type}",
            payload={"document_id": document.id, "remarks": payload.remarks},
            actor_user_id=admin_user.id,
            db=db,
        )
    await db.commit()
    return {"success": True}


@router.post("/admin/vendor-documents/{document_id}/request-resubmission")
async def request_vendor_document_resubmission(
    document_id: str,
    payload: VendorDocumentDecisionRequest,
    admin_user: User = Depends(get_current_active_superuser),
    db: AsyncSession = Depends(get_db),
):
    document = await db.get(VendorDocument, decode_id_or_404(document_id))
    if document is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vendor document not found")
    if not document.is_current:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Cannot review non-current document version")
    if document.uploaded_at.isoformat() != payload.expected_uploaded_at:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Stale document review action")
    if document.version != payload.expected_version:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Stale document version for review action")
    if document.status != VendorDocumentStatus.UNDER_REVIEW:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Document is not under review")
    assert_document_status_transition(document.status, VendorDocumentStatus.NEEDS_RESUBMISSION)
    document.status = VendorDocumentStatus.NEEDS_RESUBMISSION
    document.remarks = payload.remarks
    document.reviewed_by_user_id = admin_user.id
    document.resubmission_requested_at = utc_now()
    append_document_review_history(document, status_value=VendorDocumentStatus.NEEDS_RESUBMISSION, note=payload.remarks, actor_user_id=admin_user.id)
    vendor = await db.get(Vendor, document.vendor_id)
    if vendor:
        mark_vendor_status(vendor, VendorStatus.NEEDS_RESUBMISSION, payload.remarks)
        mark_vendor_kyc_status(vendor, kyc_status=VendorKYCStatus.RESUBMISSION_REQUIRED, reviewer_user_id=admin_user.id, reason=payload.remarks)
        await record_vendor_timeline_event(
            vendor=vendor,
            event_type="vendor.document_resubmission_requested",
            message=f"Document needs resubmission: {document.doc_type}",
            payload={"document_id": document.id, "remarks": payload.remarks},
            actor_user_id=admin_user.id,
            db=db,
        )
    await db.commit()
    return {"success": True}


@router.post("/admin/vendor-bank-accounts/{bank_account_id}/verify")
async def verify_vendor_bank_account(
    bank_account_id: str,
    admin_user: User = Depends(get_current_active_superuser),
    db: AsyncSession = Depends(get_db),
):
    bank_account = await db.get(BankAccount, decode_id_or_404(bank_account_id))
    if bank_account is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bank account not found")
    bank_account.verification_status = BankAccountVerificationStatus.VERIFIED
    bank_account.remarks = ""
    vendor = await db.get(Vendor, bank_account.vendor_id)
    if vendor:
        mark_vendor_kyc_status(vendor, kyc_status=VendorKYCStatus.UNDER_REVIEW, reviewer_user_id=admin_user.id)
        await record_vendor_timeline_event(
            vendor=vendor,
            event_type="vendor.bank_verified",
            message="Bank account verified",
            payload={"bank_account_id": bank_account.id},
            db=db,
        )
    await db.commit()
    return {"success": True}


@router.post("/admin/vendor-bank-accounts/{bank_account_id}/reject")
async def reject_vendor_bank_account(
    bank_account_id: str,
    payload: VendorDocumentReviewRequest,
    admin_user: User = Depends(get_current_active_superuser),
    db: AsyncSession = Depends(get_db),
):
    bank_account = await db.get(BankAccount, decode_id_or_404(bank_account_id))
    if bank_account is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bank account not found")
    bank_account.verification_status = BankAccountVerificationStatus.FAILED
    bank_account.remarks = payload.remarks
    vendor = await db.get(Vendor, bank_account.vendor_id)
    if vendor:
        mark_vendor_status(vendor, VendorStatus.NEEDS_RESUBMISSION, payload.remarks)
        mark_vendor_kyc_status(vendor, kyc_status=VendorKYCStatus.RESUBMISSION_REQUIRED, reviewer_user_id=admin_user.id, reason=payload.remarks)
        await record_vendor_timeline_event(
            vendor=vendor,
            event_type="vendor.bank_rejected",
            message="Bank account verification failed",
            payload={"bank_account_id": bank_account.id, "remarks": payload.remarks},
            db=db,
        )
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
        reference=f"PO-{decoded_vendor_id}-{int(utc_now().timestamp())}",
    )
    db.add(payout)
    await record_vendor_timeline_event(
        vendor=vendor,
        event_type="vendor.payout_created",
        message="Vendor payout created",
        payload={"payout_reference": payout.reference, "amount": payout.amount},
        db=db,
    )
    await db.commit()
    await db.refresh(payout)
    await notify_payout_event(
        db=db,
        user_id=vendor.owner_user_id,
        vendor_id=encode_id(vendor.id),
        event="vendor.payout_created",
        title="Vendor payout created",
        body="A payout has been created for your delivered orders.",
        amount=payout.amount,
        status=payout.status.value,
    )
    return {"payout_id": encode_id(payout.id)}


@router.get("/admin/vendor-payout-requests")
async def list_admin_vendor_payout_requests(
    _: User = Depends(get_current_active_superuser),
    db: AsyncSession = Depends(get_db),
):
    requests = (await db.execute(select(VendorPayoutRequest).order_by(VendorPayoutRequest.created_at.desc()))).scalars().all()
    return {"items": [serialize_vendor_payout_request(request) for request in requests], "total": len(requests)}


@router.post("/admin/vendor-payout-requests/{request_id}/approve")
async def approve_vendor_payout_request(
    request_id: str,
    request: Request,
    admin_user: User = Depends(get_current_active_superuser),
    db: AsyncSession = Depends(get_db),
):
    await enforce_privileged_action(
        db=db,
        request=request,
        current_user=admin_user,
        action=PrivilegedAction.PAYOUT_APPROVE,
    )
    payout_request = await db.get(VendorPayoutRequest, decode_id_or_404(request_id))
    if payout_request is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Payout request not found")
    payout_request.status = VendorPayoutStatus.PENDING
    payout_request.reviewed_at = utc_now()
    payout = VendorPayout(
        vendor_id=payout_request.vendor_id,
        amount=payout_request.amount,
        commission_amount=0,
        status=VendorPayoutStatus.PENDING,
        reference=f"REQ-{payout_request.vendor_id}-{int(utc_now().timestamp())}",
    )
    db.add(payout)
    vendor = await db.get(Vendor, payout_request.vendor_id)
    if vendor:
        await record_vendor_timeline_event(
            vendor=vendor,
            event_type="vendor.payout_request_approved",
            message="Vendor payout request approved",
            payload={"payout_request_id": payout_request.id},
            db=db,
        )
    await db.commit()
    await db.refresh(payout)
    if vendor:
        await notify_payout_event(
            db=db,
            user_id=vendor.owner_user_id,
            vendor_id=encode_id(vendor.id),
            event="vendor.payout_request_approved",
            title="Payout request approved",
            body="Your payout request has been approved.",
            amount=payout.amount,
            payout_request_id=encode_id(payout_request.id),
            status=payout.status.value,
        )
    return {"payout": serialize_vendor_payout(payout)}


@router.post("/admin/vendor-payouts/batches", status_code=status.HTTP_201_CREATED)
async def create_vendor_payout_batch(
    payload: PayoutBatchCreateRequest,
    request: Request,
    admin_user: User = Depends(get_current_active_superuser),
    db: AsyncSession = Depends(get_db),
):
    await enforce_privileged_action(
        db=db,
        request=request,
        current_user=admin_user,
        action=PrivilegedAction.PAYOUT_APPROVE,
    )
    decoded_ids = [decode_id_or_404(request_id) for request_id in payload.payout_request_ids]
    payout_requests = (
        await db.execute(select(VendorPayoutRequest).where(VendorPayoutRequest.id.in_(decoded_ids)))
    ).scalars().all() if decoded_ids else []
    batch = VendorPayoutBatch(
        code=f"BATCH-{int(utc_now().timestamp())}",
        status=VendorPayoutStatus.PENDING,
        total_amount=round(sum(request.amount for request in payout_requests), 2),
        item_count=len(payout_requests),
        notes=payload.notes,
    )
    db.add(batch)
    await db.flush()
    for request in payout_requests:
        request.status = VendorPayoutStatus.PROCESSING
        request.reviewed_at = utc_now()
        payout = VendorPayout(
            vendor_id=request.vendor_id,
            amount=request.amount,
            commission_amount=0,
            status=VendorPayoutStatus.PROCESSING,
            payout_batch_id=batch.id,
            reference=f"{batch.code}-{request.vendor_id}",
        )
        db.add(payout)
    await db.commit()
    for request in payout_requests:
        vendor = await db.get(Vendor, request.vendor_id)
        if vendor:
            await notify_payout_event(
                db=db,
                user_id=vendor.owner_user_id,
                vendor_id=encode_id(vendor.id),
                event="vendor.payout_batch_created",
                title="Payout batch created",
                body=f"Your payout request is included in batch {batch.code}.",
                amount=request.amount,
                payout_request_id=encode_id(request.id),
                payout_batch_id=encode_id(batch.id),
                status=request.status.value,
            )
    return {"batch_id": encode_id(batch.id or 0), "code": batch.code}


@router.get("/admin/vendor-payouts/batches")
async def list_vendor_payout_batches(
    _: User = Depends(get_current_active_superuser),
    db: AsyncSession = Depends(get_db),
):
    batches = (await db.execute(select(VendorPayoutBatch).order_by(VendorPayoutBatch.created_at.desc()))).scalars().all()
    return {
        "items": [
            {
                "id": encode_id(batch.id or 0),
                "code": batch.code,
                "status": batch.status.value,
                "total_amount": batch.total_amount,
                "item_count": batch.item_count,
                "notes": batch.notes,
                "created_at": batch.created_at.isoformat(),
            }
            for batch in batches
        ],
        "total": len(batches),
    }




@router.get("/admin/vendors/{vendor_id}/timeline")
async def list_admin_vendor_timeline(
    vendor_id: str,
    _: User = Depends(get_current_active_superuser),
    db: AsyncSession = Depends(get_db),
):
    vendor = await get_vendor_or_404(decode_id_or_404(vendor_id), db)
    events = (
        await db.execute(
            select(VendorTimelineEvent).where(VendorTimelineEvent.vendor_id == vendor.id).order_by(VendorTimelineEvent.created_at.desc())
        )
    ).scalars().all()
    return {
        "items": [
            {
                "id": encode_id(event.id or 0),
                "event_type": event.event_type,
                "message": event.message,
                "created_at": event.created_at.isoformat(),
                "payload": json.loads(event.payload_json or "{}"),
            }
            for event in events
        ],
        "total": len(events),
    }


@router.get("/vendor/kyc/history")
async def list_my_kyc_history(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    vendor = await get_vendor_for_user(current_user, db)
    events = (
        await db.execute(
            select(VendorTimelineEvent).where(VendorTimelineEvent.vendor_id == vendor.id).order_by(VendorTimelineEvent.created_at.desc())
        )
    ).scalars().all()
    checks = await validate_vendor_kyc_requirements(vendor, db)
    return {"kyc_status": vendor.kyc_status.value, "checks": checks, "items": serialize_vendor_kyc_timeline(events)}


@router.get("/admin/vendors/{vendor_id}/kyc/history")
async def list_admin_kyc_history(
    vendor_id: str,
    _: User = Depends(get_current_active_superuser),
    db: AsyncSession = Depends(get_db),
):
    vendor = await get_vendor_or_404(decode_id_or_404(vendor_id), db)
    events = (
        await db.execute(
            select(VendorTimelineEvent).where(VendorTimelineEvent.vendor_id == vendor.id).order_by(VendorTimelineEvent.created_at.desc())
        )
    ).scalars().all()
    checks = await validate_vendor_kyc_requirements(vendor, db)
    return {"vendor_id": encode_id(vendor.id), "kyc_status": vendor.kyc_status.value, "checks": checks, "items": serialize_vendor_kyc_timeline(events)}

@router.get("/admin/vendors/{vendor_id}/settlement-export")
async def export_vendor_settlement(
    vendor_id: str,
    _: User = Depends(get_current_active_superuser),
    db: AsyncSession = Depends(get_db),
):
    decoded_vendor_id = decode_id_or_404(vendor_id)
    payouts = (
        await db.execute(select(VendorPayout).where(VendorPayout.vendor_id == decoded_vendor_id).order_by(VendorPayout.created_at.desc()))
    ).scalars().all()
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(["reference", "amount", "commission_amount", "status", "created_at", "paid_at"])
    for payout in payouts:
        writer.writerow(
            [
                payout.reference,
                payout.amount,
                payout.commission_amount,
                payout.status.value,
                payout.created_at.isoformat(),
                payout.paid_at.isoformat() if payout.paid_at else "",
            ]
        )
    return Response(
        content=buffer.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="vendor-settlements-{decoded_vendor_id}.csv"'},
    )


def encode_id(value: int | None) -> str | None:
    if value is None:
        return None
    from src.apps.iam.utils.hashid import encode_id as _encode_id

    return _encode_id(value)

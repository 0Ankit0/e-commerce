from __future__ import annotations

import json

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from src.apps.core.time import utc_now
from src.apps.iam.models.user import User
from src.apps.multitenancy.models.tenant import Tenant, TenantMember, TenantRole
from src.apps.vendors.models import (
    Vendor,
    VendorDocument,
    VendorDocumentStatus,
    VendorKYCStatus,
    VendorPayout,
    VendorPayoutRequest,
    VendorStatus,
    VendorTimelineEvent,
    BankAccount,
    BankAccountVerificationStatus,
)

KYC_ALLOWED_TRANSITIONS: dict[VendorKYCStatus, set[VendorKYCStatus]] = {
    VendorKYCStatus.SUBMITTED: {VendorKYCStatus.UNDER_REVIEW},
    VendorKYCStatus.UNDER_REVIEW: {
        VendorKYCStatus.RESUBMISSION_REQUIRED,
        VendorKYCStatus.APPROVED,
        VendorKYCStatus.REJECTED,
    },
    VendorKYCStatus.RESUBMISSION_REQUIRED: {VendorKYCStatus.SUBMITTED, VendorKYCStatus.UNDER_REVIEW},
    VendorKYCStatus.APPROVED: {VendorKYCStatus.SUSPENDED_AFTER_APPROVAL},
    VendorKYCStatus.REJECTED: set(),
    VendorKYCStatus.SUSPENDED_AFTER_APPROVAL: set(),
}


async def require_tenant_admin(tenant_id: int, user: User, db: AsyncSession) -> Tenant:
    tenant = await db.get(Tenant, tenant_id)
    if tenant is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found")

    if user.is_superuser or tenant.owner_id == user.id:
        return tenant

    membership = (
        await db.execute(
            select(TenantMember).where(
                TenantMember.tenant_id == tenant_id,
                TenantMember.user_id == user.id,
                TenantMember.is_active == True,  # noqa: E712
            )
        )
    ).scalars().first()
    if membership and membership.role in {TenantRole.ADMIN, TenantRole.OWNER}:
        return tenant

    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Tenant admin access required")


async def get_vendor_or_404(vendor_id: int, db: AsyncSession) -> Vendor:
    vendor = await db.get(Vendor, vendor_id)
    if vendor is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vendor not found")
    return vendor


async def get_vendor_for_user(user: User, db: AsyncSession) -> Vendor:
    vendor = (
        await db.execute(select(Vendor).where(Vendor.owner_user_id == user.id))
    ).scalars().first()
    if vendor is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vendor profile not found")
    return vendor


def ensure_vendor_active(vendor: Vendor) -> None:
    if vendor.status != VendorStatus.APPROVED:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Vendor must be approved for this action",
        )


def serialize_vendor(vendor: Vendor) -> dict[str, object]:
    from src.apps.iam.utils.hashid import encode_id

    return {
        "id": encode_id(vendor.id or 0),
        "tenant_id": encode_id(vendor.tenant_id),
        "owner_user_id": encode_id(vendor.owner_user_id),
        "business_name": vendor.business_name,
        "display_name": vendor.display_name,
        "slug": vendor.slug,
        "description": vendor.description,
        "logo_url": vendor.logo_url,
        "banner_url": vendor.banner_url,
        "status": vendor.status.value,
        "kyc_status": vendor.kyc_status.value,
        "onboarding_step": vendor.onboarding_step,
        "commission_tier": vendor.commission_tier.value,
        "rating": vendor.rating,
        "rating_count": vendor.rating_count,
        "product_count": vendor.product_count,
        "verification_timeline": json.loads(vendor.verification_timeline_json or "[]"),
        "approved_at": vendor.approved_at.isoformat() if vendor.approved_at else None,
        "rejected_reason": vendor.rejected_reason,
        "kyc_submitted_at": vendor.kyc_submitted_at.isoformat() if vendor.kyc_submitted_at else None,
        "kyc_review_started_at": vendor.kyc_review_started_at.isoformat() if vendor.kyc_review_started_at else None,
        "kyc_reviewed_at": vendor.kyc_reviewed_at.isoformat() if vendor.kyc_reviewed_at else None,
        "kyc_last_reviewer_user_id": vendor.kyc_last_reviewer_user_id,
        "kyc_assigned_reviewer_user_id": vendor.kyc_assigned_reviewer_user_id,
        "kyc_reviewer_assigned_at": vendor.kyc_reviewer_assigned_at.isoformat() if vendor.kyc_reviewer_assigned_at else None,
        "kyc_review_reasons": json.loads(vendor.kyc_review_reasons_json or "[]"),
        "created_at": vendor.created_at.isoformat(),
    }


def mark_vendor_status(vendor: Vendor, status_value: VendorStatus, rejected_reason: str = "") -> None:
    vendor.status = status_value
    vendor.rejected_reason = rejected_reason
    vendor.updated_at = utc_now()
    vendor.approved_at = utc_now() if status_value == VendorStatus.APPROVED else None
    vendor.onboarding_step = {
        VendorStatus.PENDING: "profile_submitted",
        VendorStatus.UNDER_REVIEW: "under_review",
        VendorStatus.NEEDS_RESUBMISSION: "resubmission_requested",
        VendorStatus.APPROVED: "approved",
        VendorStatus.REJECTED: "rejected",
        VendorStatus.SUSPENDED: "suspended",
    }[status_value]


def mark_vendor_kyc_status(
    vendor: Vendor,
    *,
    kyc_status: VendorKYCStatus,
    reviewer_user_id: int | None = None,
    reason: str = "",
) -> None:
    allow_same_state_refresh = vendor.kyc_status == kyc_status and kyc_status in {
        VendorKYCStatus.SUBMITTED,
        VendorKYCStatus.UNDER_REVIEW,
        VendorKYCStatus.RESUBMISSION_REQUIRED,
    }
    if not allow_same_state_refresh:
        assert_vendor_kyc_transition(vendor.kyc_status, kyc_status)
    vendor.kyc_status = kyc_status
    vendor.kyc_last_reviewer_user_id = reviewer_user_id
    now = utc_now()
    if kyc_status == VendorKYCStatus.UNDER_REVIEW:
        vendor.kyc_review_started_at = now
        vendor.kyc_reviewed_at = None
    elif kyc_status in {VendorKYCStatus.APPROVED, VendorKYCStatus.REJECTED, VendorKYCStatus.RESUBMISSION_REQUIRED}:
        vendor.kyc_reviewed_at = now
    reasons = json.loads(vendor.kyc_review_reasons_json or "[]")
    if reason:
        reasons.append(
            {
                "status": kyc_status.value,
                "reason": reason,
                "reviewer_user_id": reviewer_user_id,
                "created_at": now.isoformat(),
            }
        )
    vendor.kyc_review_reasons_json = json.dumps(reasons)
    if kyc_status == VendorKYCStatus.SUBMITTED:
        vendor.kyc_submitted_at = now
        vendor.kyc_review_started_at = None
        vendor.kyc_reviewed_at = None


def assert_vendor_kyc_transition(current_status: VendorKYCStatus, target_status: VendorKYCStatus) -> None:
    if target_status not in KYC_ALLOWED_TRANSITIONS[current_status]:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Invalid KYC status transition: {current_status.value} -> {target_status.value}",
        )


async def validate_vendor_kyc_requirements(vendor: Vendor, db: AsyncSession) -> dict[str, object]:
    required_docs = {"gst", "pan"}
    current_docs = (
        await db.execute(
            select(VendorDocument).where(
                VendorDocument.vendor_id == vendor.id,
                VendorDocument.is_current == True,  # noqa: E712
            )
        )
    ).scalars().all()
    verified_doc_types = {doc.doc_type.strip().lower() for doc in current_docs if doc.status == VendorDocumentStatus.VERIFIED}
    missing_documents = sorted(required_docs - verified_doc_types)
    bank_accounts = (await db.execute(select(BankAccount).where(BankAccount.vendor_id == vendor.id))).scalars().all()
    has_verified_bank = any(bank.verification_status == BankAccountVerificationStatus.VERIFIED for bank in bank_accounts)
    return {
        "required_documents": sorted(required_docs),
        "verified_documents": sorted(verified_doc_types),
        "missing_documents": missing_documents,
        "bank_verified": has_verified_bank,
        "bank_submitted": len(bank_accounts) > 0,
    }


async def ensure_vendor_kyc_ready_for_review(vendor: Vendor, db: AsyncSession) -> None:
    required_docs = {"gst", "pan"}
    current_docs = (
        await db.execute(
            select(VendorDocument).where(
                VendorDocument.vendor_id == vendor.id,
                VendorDocument.is_current == True,  # noqa: E712
            )
        )
    ).scalars().all()
    submitted_doc_types = {doc.doc_type.strip().lower() for doc in current_docs}
    missing_documents = sorted(required_docs - submitted_doc_types)
    bank_exists = (
        await db.execute(select(BankAccount).where(BankAccount.vendor_id == vendor.id))
    ).scalars().first() is not None
    if missing_documents or not bank_exists:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "message": "KYC submission incomplete for review",
                "missing_documents": missing_documents,
                "bank_submitted": bank_exists,
                "required_documents": sorted(required_docs),
            },
        )


async def ensure_vendor_kyc_ready_for_approval(vendor: Vendor, db: AsyncSession) -> None:
    checks = await validate_vendor_kyc_requirements(vendor, db)
    if checks["missing_documents"] or not checks["bank_verified"]:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "message": "KYC requirements incomplete",
                **checks,
            },
        )


def assert_vendor_status_transition(vendor: Vendor, target_status: VendorStatus) -> None:
    allowed_transitions: dict[VendorStatus, set[VendorStatus]] = {
        VendorStatus.PENDING: {VendorStatus.UNDER_REVIEW},
        VendorStatus.UNDER_REVIEW: {
            VendorStatus.NEEDS_RESUBMISSION,
            VendorStatus.APPROVED,
            VendorStatus.REJECTED,
            VendorStatus.SUSPENDED,
        },
        VendorStatus.NEEDS_RESUBMISSION: {
            VendorStatus.UNDER_REVIEW,
            VendorStatus.REJECTED,
            VendorStatus.SUSPENDED,
        },
        VendorStatus.APPROVED: {VendorStatus.SUSPENDED},
        VendorStatus.REJECTED: set(),
        VendorStatus.SUSPENDED: set(),
    }
    if target_status not in allowed_transitions[vendor.status]:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Invalid vendor status transition: {vendor.status.value} -> {target_status.value}",
        )


def assert_document_status_transition(current_status: VendorDocumentStatus, target_status: VendorDocumentStatus) -> None:
    allowed_transitions: dict[VendorDocumentStatus, set[VendorDocumentStatus]] = {
        VendorDocumentStatus.SUBMITTED: {VendorDocumentStatus.UNDER_REVIEW},
        VendorDocumentStatus.UNDER_REVIEW: {
            VendorDocumentStatus.VERIFIED,
            VendorDocumentStatus.REJECTED,
            VendorDocumentStatus.NEEDS_RESUBMISSION,
        },
        VendorDocumentStatus.NEEDS_RESUBMISSION: {VendorDocumentStatus.SUBMITTED},
        VendorDocumentStatus.VERIFIED: set(),
        VendorDocumentStatus.REJECTED: {VendorDocumentStatus.SUBMITTED},
    }
    if target_status not in allowed_transitions[current_status]:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Invalid document status transition: {current_status.value} -> {target_status.value}",
        )


async def record_vendor_timeline_event(
    *,
    vendor: Vendor,
    event_type: str,
    message: str,
    db: AsyncSession,
    actor_user_id: int | None = None,
    payload: dict[str, object] | None = None,
) -> None:
    timeline = json.loads(vendor.verification_timeline_json or "[]")
    timeline.append(
        {
            "event_type": event_type,
            "message": message,
            "actor_user_id": actor_user_id,
            "created_at": utc_now().isoformat(),
            "payload": payload or {},
        }
    )
    vendor.verification_timeline_json = json.dumps(timeline)
    db.add(
        VendorTimelineEvent(
            vendor_id=vendor.id or 0,
            actor_user_id=actor_user_id,
            event_type=event_type,
            message=message,
            payload_json=json.dumps(payload or {}),
        )
    )




def append_document_review_history(
    document: VendorDocument,
    *,
    status_value: VendorDocumentStatus,
    note: str,
    actor_user_id: int | None,
) -> None:
    history = json.loads(document.review_reason_history_json or "[]")
    history.append(
        {
            "status": status_value.value,
            "note": note,
            "actor_user_id": actor_user_id,
            "created_at": utc_now().isoformat(),
            "version": document.version,
        }
    )
    document.review_reason_history_json = json.dumps(history)


def serialize_vendor_kyc_timeline(events: list[VendorTimelineEvent]) -> list[dict[str, object]]:
    return [
        {
            "event_type": event.event_type,
            "message": event.message,
            "actor_user_id": event.actor_user_id,
            "created_at": event.created_at.isoformat(),
            "payload": json.loads(event.payload_json or "{}"),
        }
        for event in events
        if event.event_type.startswith("vendor.") and ("kyc" in event.event_type or "document" in event.event_type or event.event_type in {"vendor.under_review", "vendor.approved", "vendor.rejected", "vendor.resubmission_requested"})
    ]


def vendor_kyc_step_status(checks: dict[str, object]) -> dict[str, str]:
    missing_documents = set(checks.get("missing_documents", []))
    return {
        "gst": "complete" if "gst" not in missing_documents else "pending",
        "pan": "complete" if "pan" not in missing_documents else "pending",
        "bank": "complete" if checks.get("bank_verified") else ("submitted" if checks.get("bank_submitted") else "pending"),
    }

def serialize_vendor_payout(payout: VendorPayout) -> dict[str, object]:
    from src.apps.iam.utils.hashid import encode_id

    return {
        "id": encode_id(payout.id or 0),
        "vendor_id": encode_id(payout.vendor_id),
        "amount": payout.amount,
        "commission_amount": payout.commission_amount,
        "status": payout.status.value,
        "reference": payout.reference,
        "period_start": payout.period_start.isoformat() if payout.period_start else None,
        "period_end": payout.period_end.isoformat() if payout.period_end else None,
        "payout_batch_id": encode_id(payout.payout_batch_id) if payout.payout_batch_id else None,
        "created_at": payout.created_at.isoformat(),
        "paid_at": payout.paid_at.isoformat() if payout.paid_at else None,
    }


def serialize_vendor_payout_request(request: VendorPayoutRequest) -> dict[str, object]:
    from src.apps.iam.utils.hashid import encode_id

    return {
        "id": encode_id(request.id or 0),
        "vendor_id": encode_id(request.vendor_id),
        "requested_by_user_id": encode_id(request.requested_by_user_id),
        "amount": request.amount,
        "currency": request.currency,
        "notes": request.notes,
        "status": request.status.value,
        "created_at": request.created_at.isoformat(),
        "reviewed_at": request.reviewed_at.isoformat() if request.reviewed_at else None,
    }

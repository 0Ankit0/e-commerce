from __future__ import annotations

import json

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from src.apps.core.time import utc_now
from src.apps.iam.models.user import User
from src.apps.multitenancy.models.tenant import Tenant, TenantMember, TenantRole
from src.apps.vendors.models import Vendor, VendorPayout, VendorPayoutRequest, VendorStatus, VendorTimelineEvent


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
        "onboarding_step": vendor.onboarding_step,
        "commission_tier": vendor.commission_tier.value,
        "rating": vendor.rating,
        "rating_count": vendor.rating_count,
        "product_count": vendor.product_count,
        "verification_timeline": json.loads(vendor.verification_timeline_json or "[]"),
        "approved_at": vendor.approved_at.isoformat() if vendor.approved_at else None,
        "rejected_reason": vendor.rejected_reason,
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


def assert_vendor_status_transition(vendor: Vendor, target_status: VendorStatus) -> None:
    allowed_transitions: dict[VendorStatus, set[VendorStatus]] = {
        VendorStatus.PENDING: {VendorStatus.UNDER_REVIEW},
        VendorStatus.UNDER_REVIEW: {VendorStatus.NEEDS_RESUBMISSION},
        VendorStatus.NEEDS_RESUBMISSION: {VendorStatus.APPROVED, VendorStatus.REJECTED, VendorStatus.SUSPENDED},
        VendorStatus.APPROVED: set(),
        VendorStatus.REJECTED: set(),
        VendorStatus.SUSPENDED: set(),
    }
    if target_status not in allowed_transitions[vendor.status]:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Invalid vendor status transition: {vendor.status.value} -> {target_status.value}",
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

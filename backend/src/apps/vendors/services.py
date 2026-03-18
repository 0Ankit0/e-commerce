from __future__ import annotations

from datetime import datetime

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from src.apps.iam.models.user import User
from src.apps.multitenancy.models.tenant import Tenant, TenantMember, TenantRole
from src.apps.vendors.models import Vendor, VendorStatus


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
        "commission_tier": vendor.commission_tier.value,
        "rating": vendor.rating,
        "rating_count": vendor.rating_count,
        "product_count": vendor.product_count,
        "approved_at": vendor.approved_at.isoformat() if vendor.approved_at else None,
        "rejected_reason": vendor.rejected_reason,
        "created_at": vendor.created_at.isoformat(),
    }


def mark_vendor_status(vendor: Vendor, status_value: VendorStatus, rejected_reason: str = "") -> None:
    vendor.status = status_value
    vendor.rejected_reason = rejected_reason
    vendor.updated_at = datetime.utcnow()
    vendor.approved_at = datetime.utcnow() if status_value == VendorStatus.APPROVED else None

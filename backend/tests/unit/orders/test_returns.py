from __future__ import annotations

from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import pytest
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from src.apps.orders.models import (
    Order,
    OrderItem,
    OrderPaymentStatus,
    OrderStatus,
    RefundRecord,
    RefundStatus,
    ReturnRequest,
    ReturnStatus,
    VendorOrderStatus,
)
from src.apps.orders.services import create_return_request, update_return_request_status


async def _create_delivered_order_with_item(db_session: AsyncSession, *, quantity: int = 3) -> tuple[Order, OrderItem]:
    order = Order(
        order_number="ORD-RET-1",
        user_id=1,
        address_id=1,
        status=OrderStatus.DELIVERED,
        payment_status=OrderPaymentStatus.PAID,
        total=300,
        delivered_at=datetime.now(timezone.utc) - timedelta(days=3),
    )
    db_session.add(order)
    await db_session.flush()
    item = OrderItem(
        order_id=order.id or 0,
        vendor_id=1,
        product_id=1,
        variant_id=1,
        product_name="Test Product",
        quantity=quantity,
        unit_price=100,
        total_price=quantity * 100,
        status=VendorOrderStatus.DELIVERED,
    )
    db_session.add(item)
    await db_session.flush()
    return order, item


@pytest.mark.asyncio
async def test_return_request_allows_exact_cutoff_boundary(db_session: AsyncSession):
    order, item = await _create_delivered_order_with_item(db_session)
    delivered_at = datetime(2026, 1, 1, tzinfo=timezone.utc)
    order.delivered_at = delivered_at

    with patch("src.apps.orders.services.utc_now", return_value=delivered_at + timedelta(days=7)):
        req = await create_return_request(
            order=order,
            user_id=1,
            order_item_id=item.id,
            reason="Boundary case",
            details="At cutoff",
            quantity=1,
            refund_method="original",
            db=db_session,
        )

    assert req.id is not None
    assert req.status == ReturnStatus.REQUESTED


@pytest.mark.asyncio
async def test_return_request_rejects_mixed_eligibility_for_order_level_return(db_session: AsyncSession):
    order, _ = await _create_delivered_order_with_item(db_session)
    db_session.add(
        OrderItem(
            order_id=order.id or 0,
            vendor_id=2,
            product_id=2,
            variant_id=2,
            product_name="In transit",
            quantity=1,
            unit_price=50,
            total_price=50,
            status=VendorOrderStatus.SHIPPED,
        )
    )
    await db_session.flush()

    with pytest.raises(HTTPException, match="mixed return eligibility"):
        await create_return_request(
            order=order,
            user_id=1,
            order_item_id=None,
            reason="Mixed states",
            details="",
            quantity=1,
            refund_method="original",
            db=db_session,
        )


@pytest.mark.asyncio
async def test_partial_quantity_respects_remaining_eligibility(db_session: AsyncSession):
    order, item = await _create_delivered_order_with_item(db_session, quantity=3)
    item.returned_quantity = 1
    db_session.add(
        ReturnRequest(
            order_id=order.id or 0,
            order_item_id=item.id,
            user_id=1,
            reason="Pending return",
            quantity=1,
            status=ReturnStatus.REQUESTED,
            refund_method="original",
        )
    )
    await db_session.flush()

    with pytest.raises(HTTPException, match="exceeds eligible quantity"):
        await create_return_request(
            order=order,
            user_id=1,
            order_item_id=item.id,
            reason="Too much",
            details="",
            quantity=2,
            refund_method="original",
            db=db_session,
        )


@pytest.mark.asyncio
async def test_refund_lifecycle_updates_refund_record_and_item_quantities(db_session: AsyncSession):
    order, item = await _create_delivered_order_with_item(db_session, quantity=2)
    req = await create_return_request(
        order=order,
        user_id=1,
        order_item_id=item.id,
        reason="Damaged",
        details="",
        quantity=2,
        refund_method="original",
        db=db_session,
    )
    await update_return_request_status(
        return_request=req,
        status_value=ReturnStatus.APPROVED,
        db=db_session,
    )
    await update_return_request_status(
        return_request=req,
        status_value=ReturnStatus.PICKED_UP,
        db=db_session,
    )
    await update_return_request_status(
        return_request=req,
        status_value=ReturnStatus.RECEIVED,
        db=db_session,
    )
    await update_return_request_status(
        return_request=req,
        status_value=ReturnStatus.REFUNDED,
        db=db_session,
    )

    refund = (await db_session.execute(select(RefundRecord).where(RefundRecord.return_request_id == req.id))).scalars().first()
    assert refund is not None
    assert refund.status == RefundStatus.COMPLETED
    assert item.returned_quantity == 2
    assert item.status == VendorOrderStatus.RETURNED
    assert order.payment_status == OrderPaymentStatus.REFUNDED

from __future__ import annotations

import pytest

from fastapi import HTTPException

from src.apps.iam.utils.hashid import encode_id
from src.apps.orders.api.v1.routes import OrderNoteCreateRequest, create_admin_order_note, list_all_orders
from src.apps.orders.models import Order, OrderPaymentStatus, OrderStatus, PaymentMethod
from src.apps.orders.references import build_order_reference, is_supported_order_reference, parse_order_reference


def test_reference_helper_accepts_current_and_legacy_and_hashid() -> None:
    current = build_order_reference()
    assert current.startswith("ORD-")
    assert is_supported_order_reference(current)
    assert is_supported_order_reference("ORD-2025-0041")
    assert is_supported_order_reference(encode_id(12))


def test_reference_helper_rejects_invalid_formats() -> None:
    assert not is_supported_order_reference("")
    assert not is_supported_order_reference("ORD-20-41")
    assert not is_supported_order_reference("ORD_2025_0041")


@pytest.mark.asyncio
async def test_admin_order_search_supports_hashid_and_legacy_reference(db_session) -> None:
    legacy_order = Order(
        order_number="ORD-2025-0041",
        user_id=1,
        address_id=1,
        status=OrderStatus.CONFIRMED,
        payment_method=PaymentMethod.COD,
        payment_status=OrderPaymentStatus.PENDING,
        total=42,
    )
    current_order = Order(
        order_number="ORD-AB12CD34EF",
        user_id=2,
        address_id=2,
        status=OrderStatus.CONFIRMED,
        payment_method=PaymentMethod.COD,
        payment_status=OrderPaymentStatus.PENDING,
        total=64,
    )
    db_session.add(legacy_order)
    db_session.add(current_order)
    await db_session.commit()

    by_legacy = await list_all_orders(q="ORD-2025-0041", _=None, db=db_session)
    assert by_legacy["total"] == 1
    assert by_legacy["items"][0]["order_number"] == "ORD-2025-0041"

    by_hashid = await list_all_orders(q=encode_id(current_order.id or 0), _=None, db=db_session)
    assert by_hashid["total"] == 1
    assert by_hashid["items"][0]["order_number"] == "ORD-AB12CD34EF"


@pytest.mark.asyncio
async def test_admin_note_rejects_unsupported_reference_format(db_session) -> None:
    with pytest.raises(HTTPException) as exc:
        await create_admin_order_note(
            order_id="ord:bad:reference",
            payload=OrderNoteCreateRequest(note="investigated"),
            current_user=None,
            db=db_session,
        )

    assert exc.value.status_code == 422


def test_parse_order_reference_normalizes_order_number() -> None:
    parsed = parse_order_reference("ord-2025-0041")
    assert parsed.normalized == "ORD-2025-0041"
    assert parsed.is_order_number is True

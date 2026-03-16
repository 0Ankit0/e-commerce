from __future__ import annotations

from decimal import Decimal

from django.utils import timezone

from apps.orders.models import Coupon, Order


class OrderActionError(Exception):
    """Raised when an order action cannot be performed."""


def calculate_coupon_discount(subtotal: Decimal, coupon: Coupon) -> Decimal:
    if coupon.discount_type == Coupon.DiscountType.PERCENTAGE:
        discount = (subtotal * coupon.discount_value) / Decimal("100")
    else:
        discount = coupon.discount_value

    if coupon.max_discount_amount is not None:
        discount = min(discount, coupon.max_discount_amount)

    return max(Decimal("0"), discount)


def cancel_order(order: Order, *, reason: str = "") -> Order:
    if not order.can_transition_to(Order.Status.CANCELLED):
        raise OrderActionError(f"Order cannot be cancelled from status '{order.status}'.")

    order.status = Order.Status.CANCELLED
    order.cancelled_at = timezone.now()
    if reason:
        order.notes = f"{order.notes}\nCancellation reason: {reason}".strip()
    order.save(update_fields=["status", "cancelled_at", "notes", "updated_at"])
    return order


def initiate_return(order: Order, *, reason: str = "") -> Order:
    if not order.can_transition_to(Order.Status.RETURN_REQUESTED):
        raise OrderActionError(f"Return cannot be requested from status '{order.status}'.")

    order.status = Order.Status.RETURN_REQUESTED
    if reason:
        order.notes = f"{order.notes}\nReturn reason: {reason}".strip()
    order.save(update_fields=["status", "notes", "updated_at"])
    return order


def get_order_tracking(order: Order) -> dict[str, str | None]:
    phase_map = {
        Order.Status.PENDING: "Order placed",
        Order.Status.CONFIRMED: "Order confirmed",
        Order.Status.PROCESSING: "Preparing shipment",
        Order.Status.PACKED: "Packed",
        Order.Status.SHIPPED: "Shipped",
        Order.Status.IN_TRANSIT: "In transit",
        Order.Status.OUT_FOR_DELIVERY: "Out for delivery",
        Order.Status.DELIVERED: "Delivered",
        Order.Status.CANCELLED: "Cancelled",
        Order.Status.RETURN_REQUESTED: "Return requested",
        Order.Status.RETURNED: "Returned",
    }
    return {
        "order_number": order.order_number,
        "status": order.status,
        "phase": phase_map.get(order.status, "Unknown"),
        "shipped_at": order.shipped_at.isoformat() if order.shipped_at else None,
        "delivered_at": order.delivered_at.isoformat() if order.delivered_at else None,
    }


def build_invoice_payload(order: Order) -> dict:
    item_count = order.items.count()
    return {
        "invoice_number": f"INV-{order.order_number}",
        "order_number": order.order_number,
        "issued_at": timezone.now().isoformat(),
        "subtotal": str(order.subtotal),
        "discount": str(order.discount),
        "tax": str(order.tax),
        "shipping_charge": str(order.shipping_charge),
        "total": str(order.total),
        "item_count": item_count,
    }

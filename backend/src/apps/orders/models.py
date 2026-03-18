from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Optional

from sqlmodel import Field, SQLModel


class OrderStatus(str, Enum):
    PENDING_PAYMENT = "pending_payment"
    CONFIRMED = "confirmed"
    PROCESSING = "processing"
    PACKED = "packed"
    SHIPPED = "shipped"
    OUT_FOR_DELIVERY = "out_for_delivery"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"
    RETURNED = "returned"


class VendorOrderStatus(str, Enum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    PACKED = "packed"
    SHIPPED = "shipped"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"
    RETURNED = "returned"


class PaymentMethod(str, Enum):
    COD = "cod"
    KHALTI = "khalti"
    ESEWA = "esewa"
    STRIPE = "stripe"
    PAYPAL = "paypal"
    WALLET = "wallet"


class OrderPaymentStatus(str, Enum):
    PENDING = "pending"
    PAID = "paid"
    FAILED = "failed"
    REFUNDED = "refunded"


class ReturnStatus(str, Enum):
    REQUESTED = "requested"
    APPROVED = "approved"
    REJECTED = "rejected"
    PICKED_UP = "picked_up"
    RECEIVED = "received"
    REFUNDED = "refunded"


class RefundStatus(str, Enum):
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"


class Order(SQLModel, table=True):
    __tablename__ = "orders"  # type: ignore[assignment]

    id: Optional[int] = Field(default=None, primary_key=True)
    order_number: str = Field(max_length=64, unique=True, index=True)
    user_id: int = Field(foreign_key="user.id", index=True)
    address_id: int = Field(foreign_key="addresses.id", index=True)
    coupon_id: Optional[int] = Field(default=None, foreign_key="coupons.id")
    status: OrderStatus = Field(default=OrderStatus.PENDING_PAYMENT)
    payment_method: PaymentMethod = Field(default=PaymentMethod.COD)
    payment_status: OrderPaymentStatus = Field(default=OrderPaymentStatus.PENDING)
    subtotal: float = Field(default=0, ge=0)
    discount: float = Field(default=0, ge=0)
    shipping_charge: float = Field(default=0, ge=0)
    tax: float = Field(default=0, ge=0)
    total: float = Field(default=0, ge=0)
    coupon_code: str = Field(default="", max_length=80)
    coupon_discount: float = Field(default=0, ge=0)
    notes: str = Field(default="", max_length=1000)
    pricing_snapshot_json: str = Field(default="{}")
    payment_transaction_id: Optional[int] = Field(
        default=None,
        foreign_key="payment_transactions.id",
        index=True,
    )
    created_at: datetime = Field(default_factory=datetime.utcnow)
    confirmed_at: Optional[datetime] = Field(default=None)
    shipped_at: Optional[datetime] = Field(default=None)
    delivered_at: Optional[datetime] = Field(default=None)
    cancelled_at: Optional[datetime] = Field(default=None)


class OrderItem(SQLModel, table=True):
    __tablename__ = "order_items"  # type: ignore[assignment]

    id: Optional[int] = Field(default=None, primary_key=True)
    order_id: int = Field(foreign_key="orders.id", index=True)
    vendor_order_id: Optional[int] = Field(default=None, foreign_key="vendor_orders.id", index=True)
    vendor_id: int = Field(foreign_key="vendors.id", index=True)
    product_id: int = Field(foreign_key="products.id", index=True)
    variant_id: int = Field(foreign_key="product_variants.id", index=True)
    product_name: str = Field(max_length=255)
    variant_name: str = Field(default="", max_length=255)
    image_url: str = Field(default="", max_length=500)
    quantity: int = Field(ge=1)
    unit_price: float = Field(ge=0)
    total_price: float = Field(ge=0)
    status: VendorOrderStatus = Field(default=VendorOrderStatus.PENDING)
    created_at: datetime = Field(default_factory=datetime.utcnow)


class VendorOrder(SQLModel, table=True):
    __tablename__ = "vendor_orders"  # type: ignore[assignment]

    id: Optional[int] = Field(default=None, primary_key=True)
    order_id: int = Field(foreign_key="orders.id", index=True)
    vendor_id: int = Field(foreign_key="vendors.id", index=True)
    vendor_order_number: str = Field(max_length=64, unique=True, index=True)
    status: VendorOrderStatus = Field(default=VendorOrderStatus.PENDING)
    subtotal: float = Field(default=0, ge=0)
    commission: float = Field(default=0, ge=0)
    vendor_amount: float = Field(default=0, ge=0)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class OrderStatusHistory(SQLModel, table=True):
    __tablename__ = "order_status_history"  # type: ignore[assignment]

    id: Optional[int] = Field(default=None, primary_key=True)
    order_id: int = Field(foreign_key="orders.id", index=True)
    status: OrderStatus = Field(default=OrderStatus.PENDING_PAYMENT)
    note: str = Field(default="", max_length=500)
    created_at: datetime = Field(default_factory=datetime.utcnow)


class ReturnRequest(SQLModel, table=True):
    __tablename__ = "return_requests"  # type: ignore[assignment]

    id: Optional[int] = Field(default=None, primary_key=True)
    order_id: int = Field(foreign_key="orders.id", index=True)
    order_item_id: Optional[int] = Field(default=None, foreign_key="order_items.id", index=True)
    user_id: int = Field(foreign_key="user.id", index=True)
    reason: str = Field(max_length=255)
    details: str = Field(default="", max_length=1000)
    refund_method: str = Field(default="original", max_length=30)
    status: ReturnStatus = Field(default=ReturnStatus.REQUESTED)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    resolved_at: Optional[datetime] = Field(default=None)


class RefundRecord(SQLModel, table=True):
    __tablename__ = "refund_records"  # type: ignore[assignment]

    id: Optional[int] = Field(default=None, primary_key=True)
    return_request_id: int = Field(foreign_key="return_requests.id", index=True)
    payment_transaction_id: Optional[int] = Field(
        default=None,
        foreign_key="payment_transactions.id",
        index=True,
    )
    amount: float = Field(ge=0)
    status: RefundStatus = Field(default=RefundStatus.PENDING)
    created_at: datetime = Field(default_factory=datetime.utcnow)


class Shipment(SQLModel, table=True):
    __tablename__ = "shipments"  # type: ignore[assignment]

    id: Optional[int] = Field(default=None, primary_key=True)
    order_id: int = Field(foreign_key="orders.id", index=True)
    vendor_order_id: Optional[int] = Field(default=None, foreign_key="vendor_orders.id", index=True)
    awb: str = Field(max_length=80, unique=True, index=True)
    status: OrderStatus = Field(default=OrderStatus.CONFIRMED)
    current_location: str = Field(default="", max_length=255)
    eta: Optional[datetime] = Field(default=None)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class ShipmentTracking(SQLModel, table=True):
    __tablename__ = "shipment_tracking"  # type: ignore[assignment]

    id: Optional[int] = Field(default=None, primary_key=True)
    shipment_id: int = Field(foreign_key="shipments.id", index=True)
    status: OrderStatus = Field(default=OrderStatus.CONFIRMED)
    location: str = Field(default="", max_length=255)
    remarks: str = Field(default="", max_length=500)
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class CheckoutIdempotency(SQLModel, table=True):
    __tablename__ = "checkout_idempotency"  # type: ignore[assignment]

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id", index=True)
    idempotency_key: str = Field(max_length=255, index=True)
    order_id: int = Field(foreign_key="orders.id", index=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)

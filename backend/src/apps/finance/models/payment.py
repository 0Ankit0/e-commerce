from datetime import datetime
from enum import Enum
from typing import Optional
from sqlmodel import Field, SQLModel

from src.apps.core.time import utc_now


class PaymentProvider(str, Enum):
    KHALTI = "khalti"
    ESEWA = "esewa"
    STRIPE = "stripe"
    PAYPAL = "paypal"
    RAZORPAY = "razorpay"
    WALLET = "wallet"
    COD = "cod"


class PaymentStatus(str, Enum):
    PENDING = "pending"
    INITIATED = "initiated"
    COMPLETED = "completed"
    FAILED = "failed"
    REFUNDED = "refunded"
    CANCELLED = "cancelled"


class PaymentTransactionBase(SQLModel):
    """Fields shared between table model and validation schemas."""
    provider: PaymentProvider = Field(
        description="Payment gateway provider"
    )
    amount: int = Field(
        description="Amount in the smallest currency unit (e.g. paisa for NPR)"
    )
    currency: str = Field(
        default="NPR",
        max_length=3,
        description="ISO 4217 currency code"
    )
    status: PaymentStatus = Field(
        default=PaymentStatus.PENDING,
        description="Current lifecycle status of the transaction"
    )
    purchase_order_id: str = Field(
        index=True,
        max_length=255,
        description="Your internal order/reference ID"
    )
    purchase_order_name: str = Field(
        max_length=255,
        description="Human-readable order description"
    )
    # Provider-assigned identifiers
    provider_transaction_id: Optional[str] = Field(
        default=None,
        index=True,
        max_length=255,
        description="Transaction ID assigned by the payment provider after initiation"
    )
    provider_pidx: Optional[str] = Field(
        default=None,
        index=True,
        max_length=255,
        description="Khalti pidx or eSewa refId — provider's unique payment index"
    )
    # Redirect / callback URLs
    return_url: str = Field(
        max_length=500,
        description="URL the provider redirects the user to after payment"
    )
    website_url: str = Field(
        default="",
        max_length=500,
        description="Merchant website URL (required by some providers)"
    )
    # Optional FK to the platform user who initiated the payment
    user_id: Optional[int] = Field(
        default=None,
        foreign_key="user.id",
        description="Platform user who initiated the payment (nullable for guest checkout)"
    )
    # Extra provider-specific data stored as JSON string
    extra_data: Optional[str] = Field(
        default=None,
        description="JSON-serialized provider-specific metadata"
    )
    failure_reason: Optional[str] = Field(
        default=None,
        max_length=500,
        description="Human-readable reason when status is FAILED"
    )
    captured_amount: int = Field(
        default=0,
        description="Total amount captured in smallest currency unit"
    )
    refunded_amount: int = Field(
        default=0,
        description="Total amount refunded in smallest currency unit"
    )
    idempotency_key: Optional[str] = Field(
        default=None,
        max_length=255,
        index=True,
        description="Idempotency key used for initiation or follow-up mutations"
    )


class PaymentTransaction(PaymentTransactionBase, table=True):
    __tablename__ = "payment_transactions" # type: ignore

    id: Optional[int] = Field(default=None, primary_key=True)
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


class PaymentWebhookBase(SQLModel):
    """Raw webhook / callback payload received from a payment provider."""
    provider: PaymentProvider = Field(description="Provider that sent the webhook")
    event_type: str = Field(
        default="callback",
        max_length=100,
        description="Provider event type (e.g. payment.completed)"
    )
    transaction_id: Optional[int] = Field(
        default=None,
        foreign_key="payment_transactions.id",
        description="Linked transaction (resolved after matching)"
    )
    raw_payload: str = Field(
        description="Raw JSON payload from the provider"
    )
    is_verified: bool = Field(
        default=False,
        description="Whether the webhook signature/data has been verified"
    )
    ip_address: Optional[str] = Field(
        default=None,
        max_length=45,
        description="IP address the webhook was received from"
    )


class PaymentWebhook(PaymentWebhookBase, table=True):
    __tablename__ = "payment_webhooks" # type: ignore

    id: Optional[int] = Field(default=None, primary_key=True)
    received_at: datetime = Field(default_factory=utc_now)


class PaymentRefundStatus(str, Enum):
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"


class PaymentRefund(SQLModel, table=True):
    __tablename__ = "payment_refunds"  # type: ignore

    id: Optional[int] = Field(default=None, primary_key=True)
    transaction_id: int = Field(foreign_key="payment_transactions.id", index=True)
    amount: int = Field(description="Refund amount in the smallest currency unit")
    status: PaymentRefundStatus = Field(default=PaymentRefundStatus.PENDING)
    destination: str = Field(default="original", max_length=50)
    reason: str = Field(default="", max_length=255)
    provider_refund_id: Optional[str] = Field(default=None, max_length=255)
    created_at: datetime = Field(default_factory=utc_now)


class PaymentAudit(SQLModel, table=True):
    __tablename__ = "payment_audit_logs"  # type: ignore

    id: Optional[int] = Field(default=None, primary_key=True)
    transaction_id: Optional[int] = Field(default=None, foreign_key="payment_transactions.id", index=True)
    event_type: str = Field(max_length=100, index=True)
    actor_user_id: Optional[int] = Field(default=None, foreign_key="user.id", index=True)
    payload_json: str = Field(default="{}")
    created_at: datetime = Field(default_factory=utc_now)

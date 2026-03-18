"""
Finance payment API endpoints (v1).

POST /payments/initiate     — initiate a payment with any provider
POST /payments/verify       — verify / process a provider callback
GET  /payments/{id}         — retrieve a stored transaction record
GET  /payments/             — list transactions (authenticated users)
"""
import hashlib
import hmac
import json
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select, col

from src.apps.core.config import settings

from src.apps.finance.models.payment import (
    PaymentAudit,
    PaymentProvider,
    PaymentRefund,
    PaymentRefundStatus,
    PaymentStatus,
    PaymentTransaction,
    PaymentWebhook,
)
from src.apps.finance.models.stored_value import GiftCard, WalletLedger, WalletLedgerType
from src.apps.finance.schemas.payment import (
    InitiatePaymentRequest,
    InitiatePaymentResponse,
    PaymentCaptureRequest,
    PaymentRefundCreateRequest,
    PaymentRefundRead,
    PaymentTransactionRead,
    VerifyPaymentRequest,
    VerifyPaymentResponse,
)
from src.apps.finance.services.base import BasePaymentProvider
from src.apps.finance.services.esewa import EsewaService
from src.apps.finance.services.khalti import KhaltiService
from src.apps.finance.services.stripe import StripeService
from src.apps.finance.services.paypal import PayPalService
from src.apps.finance.services.stored_value import create_wallet_entry, get_wallet_balance, redeem_gift_card
from src.apps.iam.api.deps import get_current_active_superuser, get_current_user, get_db
from src.apps.iam.models.user import User
from src.apps.iam.utils.hashid import decode_id_or_404, encode_id
from src.apps.analytics.dependencies import get_analytics
from src.apps.analytics.service import AnalyticsService
from src.apps.analytics.events import PaymentEvents

router = APIRouter()


def _decode_transaction_identifier(transaction_id: str) -> int:
    if transaction_id.isdigit():
        return int(transaction_id)
    return decode_id_or_404(transaction_id)

# ---------------------------------------------------------------------------
# Provider registry — built at startup, respects per-provider enabled flags
# ---------------------------------------------------------------------------

def _build_registry() -> dict[PaymentProvider, BasePaymentProvider]:
    registry: dict[PaymentProvider, BasePaymentProvider] = {}
    if settings.KHALTI_ENABLED:
        registry[PaymentProvider.KHALTI] = KhaltiService()
    if settings.ESEWA_ENABLED:
        registry[PaymentProvider.ESEWA] = EsewaService()
    if settings.STRIPE_ENABLED:
        registry[PaymentProvider.STRIPE] = StripeService()
    if settings.PAYPAL_ENABLED:
        registry[PaymentProvider.PAYPAL] = PayPalService()
    return registry

_PROVIDERS: dict[PaymentProvider, BasePaymentProvider] = _build_registry()


def _webhook_secret_for(provider: PaymentProvider) -> str:
    if provider == PaymentProvider.STRIPE:
        return settings.STRIPE_WEBHOOK_SECRET
    if provider == PaymentProvider.PAYPAL:
        return settings.PAYPAL_CLIENT_SECRET
    if provider == PaymentProvider.KHALTI:
        return settings.KHALTI_SECRET_KEY
    if provider == PaymentProvider.ESEWA:
        return settings.ESEWA_SECRET_KEY
    return ""


def _is_valid_webhook_signature(*, raw_body: bytes, provided_signature: str, secret: str) -> bool:
    if not secret or not provided_signature:
        return False
    expected_hmac = hmac.new(secret.encode("utf-8"), raw_body, hashlib.sha256).hexdigest()
    normalized_signature = provided_signature.removeprefix("sha256=").strip()
    return hmac.compare_digest(normalized_signature, expected_hmac) or hmac.compare_digest(provided_signature, secret)


def _serialize_wallet_entry(entry: WalletLedger) -> dict[str, object]:
    return {
        "id": encode_id(entry.id or 0),
        "entry_type": entry.entry_type.value,
        "amount": entry.amount,
        "balance_after": entry.balance_after,
        "reference_type": entry.reference_type,
        "reference_id": encode_id(entry.reference_id) if entry.reference_id else None,
        "notes": entry.notes,
        "created_at": entry.created_at.isoformat(),
    }


async def _log_payment_audit(
    *,
    event_type: str,
    transaction_id: int | None,
    actor_user_id: int | None,
    payload: dict[str, object],
    db: AsyncSession,
) -> None:
    db.add(
        PaymentAudit(
            transaction_id=transaction_id,
            event_type=event_type,
            actor_user_id=actor_user_id,
            payload_json=json.dumps(payload),
        )
    )


def _describe_exception(exc: Exception) -> str:
    """Format exceptions so blank provider errors remain actionable."""
    message = str(exc).strip()
    if message:
        return message
    return f"{exc.__class__.__name__}: {exc!r}"


def _get_provider(provider: PaymentProvider) -> BasePaymentProvider:
    svc = _PROVIDERS.get(provider)
    if svc is None:
        # Distinguish "disabled" from "unknown"
        known = {p.value for p in PaymentProvider}
        if provider.value in known:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"Payment provider '{provider}' is currently disabled.",
            )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Payment provider '{provider}' is not supported.",
        )
    return svc


async def _sync_order_after_transaction(
    tx: PaymentTransaction,
    db: AsyncSession,
) -> None:
    from src.apps.orders.models import Order, OrderPaymentStatus, OrderStatus
    from src.apps.orders.services import cancel_order, confirm_order_payment

    order = (
        await db.execute(select(Order).where(Order.payment_transaction_id == tx.id))
    ).scalars().first()
    if order is None:
        order = (await db.execute(select(Order).where(Order.order_number == tx.purchase_order_id))).scalars().first()
        if order is not None and order.payment_transaction_id is None:
            order.payment_transaction_id = tx.id
    if order is None:
        return

    if tx.status == PaymentStatus.COMPLETED:
        await confirm_order_payment(order, db)
    elif tx.status == PaymentStatus.CANCELLED and order.status == OrderStatus.PENDING_PAYMENT:
        await cancel_order(order, db)
        order.payment_status = OrderPaymentStatus.FAILED
    elif tx.status == PaymentStatus.REFUNDED:
        order.payment_status = OrderPaymentStatus.REFUNDED


# ---------------------------------------------------------------------------
# List enabled providers
# ---------------------------------------------------------------------------

@router.get("/providers/", response_model=list[str])
async def list_enabled_providers() -> list[str]:
    """Return the list of currently enabled payment providers."""
    return [p.value for p in _PROVIDERS]


# ---------------------------------------------------------------------------
# Initiate payment
# ---------------------------------------------------------------------------

@router.post("/initiate/", response_model=InitiatePaymentResponse)
async def initiate_payment(
    request_body: InitiatePaymentRequest,
    db: AsyncSession = Depends(get_db),
    analytics: AnalyticsService = Depends(get_analytics),
) -> InitiatePaymentResponse:
    """
    Initiate a new payment with the specified provider.

    Returns the payment URL (Khalti) or form fields (eSewa) the client
    should use to redirect / submit the user to the provider's checkout.
    """
    provider_svc = _get_provider(request_body.provider)
    try:
        result = await provider_svc.initiate_payment(request_body, db)
        distinct_id = str(result.transaction_id)
        await analytics.capture(
            distinct_id,
            PaymentEvents.PAYMENT_INITIATED,
            {
                "provider": request_body.provider.value,
                "amount": request_body.amount,
                "purchase_order_id": request_body.purchase_order_id,
                "transaction_id": result.transaction_id,
            },
        )
        return result
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Payment provider error: {_describe_exception(exc)}",
        )


@router.post("/intents/", response_model=InitiatePaymentResponse)
async def create_payment_intent(
    request_body: InitiatePaymentRequest,
    db: AsyncSession = Depends(get_db),
    analytics: AnalyticsService = Depends(get_analytics),
) -> InitiatePaymentResponse:
    return await initiate_payment(request_body, db, analytics)


# ---------------------------------------------------------------------------
# Verify payment
# ---------------------------------------------------------------------------

@router.post("/verify/", response_model=VerifyPaymentResponse)
async def verify_payment(
    request_body: VerifyPaymentRequest,
    db: AsyncSession = Depends(get_db),
    analytics: AnalyticsService = Depends(get_analytics),
) -> VerifyPaymentResponse:
    """
    Verify a payment after the provider redirects the user back.

    - **Khalti**: send ``provider=khalti`` and ``pidx`` received in callback.
    - **eSewa**: send ``provider=esewa`` and the base64 ``data`` param from callback.
    """
    provider_svc = _get_provider(request_body.provider)
    try:
        result = await provider_svc.verify_payment(request_body, db)
        tx = await db.get(PaymentTransaction, result.transaction_id)
        if tx is not None:
            await _sync_order_after_transaction(tx, db)
        from src.apps.finance.models.payment import PaymentStatus
        event = (
            PaymentEvents.PAYMENT_COMPLETED
            if result.status == PaymentStatus.COMPLETED
            else PaymentEvents.PAYMENT_FAILED
        )
        await analytics.capture(
            str(result.transaction_id),
            event,
            {
                "provider": request_body.provider.value,
                "status": result.status.value,
                "amount": result.amount,
                "transaction_id": result.transaction_id,
            },
        )
        return result
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Payment provider error: {_describe_exception(exc)}",
        )


@router.post("/webhooks/{provider}")
async def ingest_payment_webhook(
    provider: PaymentProvider,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    raw_body = await request.body()
    provided_signature = request.headers.get("X-Webhook-Signature", "")
    expected_signature = _webhook_secret_for(provider)
    is_verified = _is_valid_webhook_signature(
        raw_body=raw_body,
        provided_signature=provided_signature,
        secret=expected_signature,
    )
    webhook = PaymentWebhook(
        provider=provider,
        event_type=request.headers.get("X-Webhook-Event", "callback"),
        raw_payload=raw_body.decode("utf-8"),
        is_verified=is_verified,
        ip_address=request.client.host if request.client else None,
    )
    db.add(webhook)
    await db.flush()
    if not is_verified:
        await db.commit()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid webhook signature")
    payload: dict[str, object] = {}
    try:
        payload = json.loads(raw_body.decode("utf-8") or "{}")
    except json.JSONDecodeError:
        payload = {}
    provider_pidx = str(payload.get("provider_pidx") or payload.get("pidx") or payload.get("session_id") or "")
    tx = None
    if provider_pidx:
        tx = (
            await db.execute(
                select(PaymentTransaction).where(
                    PaymentTransaction.provider == provider,
                    PaymentTransaction.provider_pidx == provider_pidx,
                )
            )
        ).scalars().first()
    if tx:
        event_type = webhook.event_type.lower()
        if "refund" in event_type:
            tx.status = PaymentStatus.REFUNDED
            tx.refunded_amount = tx.amount
        elif "cancel" in event_type:
            tx.status = PaymentStatus.CANCELLED
        else:
            tx.status = PaymentStatus.COMPLETED
            tx.captured_amount = tx.amount
        webhook.transaction_id = tx.id
        await _sync_order_after_transaction(tx, db)
        await _log_payment_audit(
            event_type="webhook.received",
            transaction_id=tx.id,
            actor_user_id=None,
            payload=payload,
            db=db,
        )
    await db.commit()
    return {"received": True, "verified": True}


# ---------------------------------------------------------------------------
# Retrieve a single transaction
# ---------------------------------------------------------------------------

@router.get("/{transaction_id}/", response_model=PaymentTransactionRead)
async def get_transaction(
    transaction_id: str,
    db: AsyncSession = Depends(get_db),
) -> PaymentTransactionRead:
    """Fetch a stored payment transaction by its internal ID."""
    decoded_transaction_id = _decode_transaction_identifier(transaction_id)
    tx = await db.get(PaymentTransaction, decoded_transaction_id)
    if tx is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Transaction {transaction_id} not found.",
        )
    return PaymentTransactionRead.model_validate(tx)


@router.post("/{transaction_id}/capture/", response_model=PaymentTransactionRead)
async def capture_transaction(
    transaction_id: str,
    payload: PaymentCaptureRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> PaymentTransactionRead:
    tx = await db.get(PaymentTransaction, _decode_transaction_identifier(transaction_id))
    if tx is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Transaction not found")
    if tx.status not in {PaymentStatus.INITIATED, PaymentStatus.PENDING, PaymentStatus.COMPLETED}:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Transaction cannot be captured")
    capture_amount = payload.amount or tx.amount
    if capture_amount <= 0 or capture_amount > tx.amount:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid capture amount")
    tx.captured_amount = capture_amount
    tx.status = PaymentStatus.COMPLETED
    await _sync_order_after_transaction(tx, db)
    await _log_payment_audit(
        event_type="capture",
        transaction_id=tx.id,
        actor_user_id=current_user.id,
        payload={"amount": capture_amount},
        db=db,
    )
    await db.commit()
    await db.refresh(tx)
    return PaymentTransactionRead.model_validate(tx)


@router.post("/{transaction_id}/void/", response_model=PaymentTransactionRead)
async def void_transaction(
    transaction_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> PaymentTransactionRead:
    tx = await db.get(PaymentTransaction, _decode_transaction_identifier(transaction_id))
    if tx is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Transaction not found")
    if tx.status not in {PaymentStatus.INITIATED, PaymentStatus.PENDING}:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Transaction cannot be voided")
    tx.status = PaymentStatus.CANCELLED
    await _sync_order_after_transaction(tx, db)
    await _log_payment_audit(
        event_type="void",
        transaction_id=tx.id,
        actor_user_id=current_user.id,
        payload={},
        db=db,
    )
    await db.commit()
    await db.refresh(tx)
    return PaymentTransactionRead.model_validate(tx)


@router.post("/{transaction_id}/refunds/", response_model=PaymentRefundRead)
async def refund_transaction(
    transaction_id: str,
    payload: PaymentRefundCreateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> PaymentRefundRead:
    tx = await db.get(PaymentTransaction, _decode_transaction_identifier(transaction_id))
    if tx is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Transaction not found")
    if tx.status not in {PaymentStatus.COMPLETED, PaymentStatus.REFUNDED}:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Transaction cannot be refunded")
    if tx.refunded_amount + payload.amount > tx.captured_amount:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Refund amount exceeds captured amount")
    refund = PaymentRefund(
        transaction_id=tx.id,
        amount=payload.amount,
        status=PaymentRefundStatus.COMPLETED,
        destination=payload.destination,
        reason=payload.reason,
        provider_refund_id=f"refund-{tx.id}-{tx.refunded_amount + payload.amount}",
    )
    db.add(refund)
    tx.refunded_amount += payload.amount
    if tx.refunded_amount >= tx.captured_amount:
        tx.status = PaymentStatus.REFUNDED
    await _sync_order_after_transaction(tx, db)
    if payload.destination == "wallet" and tx.user_id:
        await create_wallet_entry(
            user_id=tx.user_id,
            amount=payload.amount,
            entry_type=WalletLedgerType.REFUND,
            reference_type="payment_refund",
            reference_id=tx.id,
            notes=payload.reason or "Wallet refund",
            db=db,
        )
    await _log_payment_audit(
        event_type="refund",
        transaction_id=tx.id,
        actor_user_id=current_user.id,
        payload=payload.model_dump(),
        db=db,
    )
    await db.commit()
    await db.refresh(refund)
    return PaymentRefundRead.model_validate(refund)


# ---------------------------------------------------------------------------
# List transactions (with optional filters)
# ---------------------------------------------------------------------------

@router.get("/", response_model=list[PaymentTransactionRead])
async def list_transactions(
    provider: Optional[PaymentProvider] = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db),
) -> list[PaymentTransactionRead]:
    """List payment transactions with optional provider filter."""
    query = select(PaymentTransaction).order_by(
        col(PaymentTransaction.id).desc()
    ).limit(limit).offset(offset)

    if provider:
        query = query.where(PaymentTransaction.provider == provider)

    result = await db.execute(query)
    transactions = result.scalars().all()
    return [PaymentTransactionRead.model_validate(tx) for tx in transactions]


@router.get("/stored-value/wallet/")
async def get_wallet(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    balance = await get_wallet_balance(current_user.id, db)
    entries = (
        await db.execute(select(WalletLedger).where(WalletLedger.user_id == current_user.id).order_by(col(WalletLedger.id).desc()))
    ).scalars().all()
    return {"balance": balance, "entries": [_serialize_wallet_entry(entry) for entry in entries]}


@router.post("/stored-value/wallet/credit")
async def admin_credit_wallet(
    amount: int = Query(..., gt=0),
    user_id: str = Query(...),
    _: User = Depends(get_current_active_superuser),
    db: AsyncSession = Depends(get_db),
):
    decoded_user_id = decode_id_or_404(user_id)
    entry = await create_wallet_entry(
        user_id=decoded_user_id,
        amount=amount,
        entry_type=WalletLedgerType.CREDIT,
        reference_type="admin_credit",
        reference_id=None,
        notes="Admin wallet credit",
        db=db,
    )
    await db.commit()
    return {"entry": _serialize_wallet_entry(entry)}


@router.post("/stored-value/gift-cards/")
async def create_gift_card(
    amount: int = Query(..., gt=0),
    code: str = Query(..., min_length=4),
    _: User = Depends(get_current_active_superuser),
    db: AsyncSession = Depends(get_db),
):
    existing = (await db.execute(select(GiftCard).where(GiftCard.code == code.upper()))).scalars().first()
    if existing:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Gift card code already exists")
    gift_card = GiftCard(code=code.upper(), initial_amount=amount, remaining_amount=amount)
    db.add(gift_card)
    await db.commit()
    await db.refresh(gift_card)
    return {"gift_card": {"id": encode_id(gift_card.id or 0), "code": gift_card.code, "amount": gift_card.remaining_amount}}


@router.post("/stored-value/gift-cards/redeem/")
async def redeem_gift_card_endpoint(
    code: str = Query(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    gift_card = await redeem_gift_card(code, current_user.id, db)
    await db.commit()
    balance = await get_wallet_balance(current_user.id, db)
    return {"gift_card_code": gift_card.code, "wallet_balance": balance}

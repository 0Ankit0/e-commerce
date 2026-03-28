import hashlib
import hmac
import json

import httpx
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from src.apps.core.config import settings
from src.apps.core.time import utc_now
from src.apps.finance.models.payment import PaymentProvider, PaymentStatus, PaymentTransaction
from src.apps.finance.schemas.payment import (
    InitiatePaymentRequest,
    InitiatePaymentResponse,
    VerifyPaymentRequest,
    VerifyPaymentResponse,
)
from src.apps.finance.services.base import BasePaymentProvider


class RazorpayService(BasePaymentProvider):
    """Razorpay payment provider integration using HTTP APIs."""

    def __init__(self) -> None:
        self._base_url = settings.RAZORPAY_BASE_URL.rstrip("/")

    def _client(self) -> httpx.AsyncClient:
        return httpx.AsyncClient(
            base_url=self._base_url,
            auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET),
            timeout=settings.HTTP_TIMEOUT_SECONDS,
        )

    async def initiate_payment(
        self,
        request: InitiatePaymentRequest,
        db: AsyncSession,
    ) -> InitiatePaymentResponse:
        payload = {
            "amount": request.amount,
            "currency": "INR",
            "receipt": request.purchase_order_id,
            "notes": {
                "purchase_order_name": request.purchase_order_name,
                "return_url": request.return_url,
                "website_url": request.website_url,
            },
        }

        async with self._client() as client:
            response = await client.post("/v1/orders", json=payload)
            response.raise_for_status()
            order = response.json()

        tx = PaymentTransaction(
            provider=PaymentProvider.RAZORPAY,
            amount=request.amount,
            currency="INR",
            purchase_order_id=request.purchase_order_id,
            purchase_order_name=request.purchase_order_name,
            return_url=request.return_url,
            website_url=request.website_url,
            status=PaymentStatus.INITIATED,
            provider_pidx=order["id"],
            extra_data=json.dumps({"order": order}),
        )
        db.add(tx)
        await db.commit()
        await db.refresh(tx)

        return InitiatePaymentResponse(
            transaction_id=tx.id,
            provider=PaymentProvider.RAZORPAY,
            status=PaymentStatus.INITIATED,
            payment_url=f"https://checkout.razorpay.com/v1/checkout.js?order_id={order['id']}",
            provider_pidx=order["id"],
            extra={"order_id": order["id"], "key_id": settings.RAZORPAY_KEY_ID},
        )

    async def verify_payment(
        self,
        request: VerifyPaymentRequest,
        db: AsyncSession,
    ) -> VerifyPaymentResponse:
        payment_id = request.pidx
        order_id = request.oid
        signature = request.refId

        if not payment_id:
            raise ValueError("payment_id (pidx) is required for Razorpay verification")

        if order_id:
            result = await db.execute(
                select(PaymentTransaction).where(
                    PaymentTransaction.provider == PaymentProvider.RAZORPAY,
                    PaymentTransaction.provider_pidx == order_id,
                )
            )
            tx: PaymentTransaction | None = result.scalars().first()
        else:
            tx = None

        if tx is None and order_id:
            tx_result = await db.execute(
                select(PaymentTransaction).where(
                    PaymentTransaction.provider == PaymentProvider.RAZORPAY,
                    PaymentTransaction.purchase_order_id == order_id,
                )
            )
            tx = tx_result.scalars().first()
        if tx is None:
            tx = (
                await db.execute(
                    select(PaymentTransaction).where(
                        PaymentTransaction.provider == PaymentProvider.RAZORPAY,
                        PaymentTransaction.status.in_([PaymentStatus.INITIATED, PaymentStatus.PENDING]),
                    )
                )
            ).scalars().first()
        if tx is None:
            raise ValueError("No Razorpay transaction found for verification")

        if order_id and signature:
            body = f"{order_id}|{payment_id}".encode("utf-8")
            expected = hmac.new(
                settings.RAZORPAY_KEY_SECRET.encode("utf-8"),
                body,
                hashlib.sha256,
            ).hexdigest()
            if not hmac.compare_digest(expected, signature):
                tx.status = PaymentStatus.FAILED
                tx.failure_reason = "Razorpay signature verification failed"
                tx.updated_at = utc_now()
                db.add(tx)
                await db.commit()
                await db.refresh(tx)
                raise ValueError("Invalid Razorpay signature")

        async with self._client() as client:
            response = await client.get(f"/v1/payments/{payment_id}")
            response.raise_for_status()
            payment = response.json()

        provider_status = str(payment.get("status", "")).lower()
        if provider_status in {"captured", "authorized"}:
            status = PaymentStatus.COMPLETED
        elif provider_status in {"created", "pending"}:
            status = PaymentStatus.PENDING
        elif provider_status in {"failed", "cancelled"}:
            status = PaymentStatus.FAILED
        else:
            status = PaymentStatus.FAILED

        tx.status = status
        tx.provider_transaction_id = payment_id
        tx.provider_pidx = order_id or tx.provider_pidx
        tx.extra_data = json.dumps({"payment": payment})
        tx.updated_at = utc_now()
        db.add(tx)
        await db.commit()
        await db.refresh(tx)

        return VerifyPaymentResponse(
            transaction_id=tx.id,
            provider=PaymentProvider.RAZORPAY,
            status=tx.status,
            amount=tx.amount,
            provider_transaction_id=payment_id,
            extra={"order_id": tx.provider_pidx, "payment_id": payment_id, "status": provider_status},
        )

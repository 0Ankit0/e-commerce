from collections.abc import Mapping
from typing import Any

from django.conf import settings

from apps.integrations.services import StripeService


class StripePaymentService:
    def __init__(self):
        self._service = StripeService()

    def create_payment_intent(self, *, amount: int, currency: str, metadata: dict[str, Any]) -> dict[str, Any]:
        return self._service.create_payment_intent(amount=amount, currency=currency, metadata=metadata)

    def retrieve_payment_intent(self, payment_intent_id: str) -> Mapping[str, Any]:
        return self._service.stripe.PaymentIntent.retrieve(payment_intent_id)

    def construct_event(self, payload: bytes, signature: str) -> Mapping[str, Any]:
        return self._service.stripe.Webhook.construct_event(payload, signature, settings.DJSTRIPE_WEBHOOK_SECRET)

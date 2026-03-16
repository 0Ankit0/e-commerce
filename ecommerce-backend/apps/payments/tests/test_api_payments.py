from decimal import Decimal
from unittest.mock import patch

from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.orders.models import Order
from apps.payments.models import Payment, PaymentWebhookEvent
from apps.users.models import Address, User


class PaymentApiTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(email="payments@example.com", password="password")
        self.address = Address.objects.create(
            user=self.user,
            name="Home",
            line1="123 Main St",
            city="Test City",
            state="Test State",
            pincode="123456",
            country="US",
        )
        self.order = Order.objects.create(
            order_number="ORD-PAY-001",
            user=self.user,
            address=self.address,
            payment_method=Order.PaymentMethodChoices.CARD,
            subtotal=Decimal("100.00"),
            total=Decimal("100.00"),
        )

    def test_gateway_webhook_rejects_invalid_signature(self):
        url = reverse("payments-webhook")

        response = self.client.post(url, {}, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data["detail"], "Missing Stripe-Signature header.")

    @patch("apps.payments.api.views.StripePaymentService.construct_event")
    def test_gateway_webhook_ignores_duplicate_events(self, construct_event_mock):
        payment = Payment.objects.create(
            order=self.order,
            gateway=Payment.Gateway.STRIPE,
            method=Payment.Method.CARD,
            status=Payment.Status.PENDING,
            amount=Decimal("100.00"),
            currency="USD",
            gateway_payment_id="pi_test_123",
            gateway_order_id="pi_test_123",
        )
        event = {
            "id": "evt_duplicate_1",
            "type": "payment_intent.succeeded",
            "data": {"object": {"id": "pi_test_123", "status": "succeeded"}},
        }
        construct_event_mock.return_value = event

        url = reverse("payments-webhook")
        first = self.client.post(url, {}, format="json", HTTP_STRIPE_SIGNATURE="valid")
        second = self.client.post(url, {}, format="json", HTTP_STRIPE_SIGNATURE="valid")

        payment.refresh_from_db()
        self.assertEqual(first.status_code, status.HTTP_200_OK)
        self.assertEqual(second.status_code, status.HTTP_200_OK)
        self.assertEqual(second.data, {"duplicate": True})
        self.assertEqual(payment.status, Payment.Status.CAPTURED)
        self.assertEqual(PaymentWebhookEvent.objects.filter(event_id="evt_duplicate_1").count(), 1)

    @patch("apps.payments.api.views.StripePaymentService.retrieve_payment_intent")
    def test_verify_payment_updates_status_and_is_idempotent(self, retrieve_intent_mock):
        self.client.force_authenticate(user=self.user)
        payment = Payment.objects.create(
            order=self.order,
            gateway=Payment.Gateway.STRIPE,
            method=Payment.Method.CARD,
            status=Payment.Status.PENDING,
            amount=Decimal("100.00"),
            currency="USD",
            gateway_payment_id="pi_verify_123",
            gateway_order_id="pi_verify_123",
        )
        retrieve_intent_mock.return_value = {"id": "pi_verify_123", "status": "succeeded"}

        url = reverse("payments-verify")
        payload = {"payment_id": str(payment.id), "gateway_payment_id": "pi_verify_123"}

        first = self.client.post(url, payload, format="json", HTTP_IDEMPOTENCY_KEY="verify-1")
        second = self.client.post(url, payload, format="json", HTTP_IDEMPOTENCY_KEY="verify-1")

        payment.refresh_from_db()
        self.order.refresh_from_db()

        self.assertEqual(first.status_code, status.HTTP_200_OK)
        self.assertEqual(second.status_code, status.HTTP_200_OK)
        self.assertEqual(payment.status, Payment.Status.CAPTURED)
        self.assertEqual(self.order.payment_status, Order.PaymentStatusChoices.CAPTURED)
        self.assertEqual(retrieve_intent_mock.call_count, 1)

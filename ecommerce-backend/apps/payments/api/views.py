from decimal import Decimal

from django.db import IntegrityError, transaction
from django.utils import timezone
from hashid_field import rest
from rest_framework import permissions, serializers, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.orders.models import Order
from apps.payments.models import Payment, PaymentIdempotency, PaymentWebhookEvent, Refund
from apps.payments.serializers import PaymentSerializer, RefundSerializer
from apps.payments.services.stripe_payment_service import StripePaymentService


class CreatePaymentRequestSerializer(serializers.Serializer):
    order_id = rest.HashidSerializerCharField(source_field="orders.Order.id")
    amount = serializers.DecimalField(max_digits=12, decimal_places=2)
    currency = serializers.CharField(max_length=3, default="USD")
    method = serializers.ChoiceField(choices=Payment.Method.choices, default=Payment.Method.CARD)
    gateway = serializers.ChoiceField(choices=Payment.Gateway.choices, default=Payment.Gateway.STRIPE)


class VerifyPaymentRequestSerializer(serializers.Serializer):
    payment_id = rest.HashidSerializerCharField(source_field="payments.Payment.id")
    gateway_payment_id = serializers.CharField(required=False, allow_blank=False)


class PaymentViewSet(viewsets.ModelViewSet):
    queryset = Payment.objects.all()
    serializer_class = PaymentSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return super().get_queryset().filter(order__user=self.request.user)

    @staticmethod
    def _save_idempotency_response(request, action: str, payload: dict, status_code: int):
        key = request.headers.get("Idempotency-Key")
        if not key:
            return

        try:
            PaymentIdempotency.objects.create(
                user=request.user,
                action=action,
                key=key,
                response_data=payload,
                status_code=status_code,
            )
        except IntegrityError:
            return

    @staticmethod
    def _get_idempotency_response(request, action: str):
        key = request.headers.get("Idempotency-Key")
        if not key:
            return None

        entry = PaymentIdempotency.objects.filter(user=request.user, action=action, key=key).first()
        if not entry:
            return None
        return Response(entry.response_data, status=entry.status_code)

    @staticmethod
    def _apply_payment_status(payment: Payment, gateway_status: str, gateway_payload: dict):
        status_mapping = {
            "succeeded": Payment.Status.CAPTURED,
            "requires_capture": Payment.Status.AUTHORIZED,
            "processing": Payment.Status.AUTHORIZED,
            "requires_action": Payment.Status.PENDING,
            "requires_payment_method": Payment.Status.FAILED,
            "canceled": Payment.Status.FAILED,
        }
        target_status = status_mapping.get(gateway_status, Payment.Status.PENDING)
        payment.gateway_response = gateway_payload
        if payment.can_transition_to(target_status):
            payment.status = target_status
            if target_status == Payment.Status.AUTHORIZED and not payment.authorized_at:
                payment.authorized_at = timezone.now()
            if target_status == Payment.Status.CAPTURED and not payment.captured_at:
                payment.captured_at = timezone.now()
            if target_status in {Payment.Status.AUTHORIZED, Payment.Status.CAPTURED, Payment.Status.FAILED}:
                payment.order.payment_status = target_status
                payment.order.save(update_fields=["payment_status", "updated_at"])
        payment.save()

    @action(detail=False, methods=["post"], url_path="create")
    def create_payment(self, request):
        if idempotent_response := self._get_idempotency_response(request, PaymentIdempotency.Action.CREATE):
            return idempotent_response

        serializer = CreatePaymentRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        order = Order.objects.filter(id=data["order_id"], user=request.user).first()
        if not order:
            payload = {"detail": "Order not found."}
            self._save_idempotency_response(request, PaymentIdempotency.Action.CREATE, payload, status.HTTP_404_NOT_FOUND)
            return Response(payload, status=status.HTTP_404_NOT_FOUND)

        if data["gateway"] != Payment.Gateway.STRIPE:
            payload = {"detail": "Only Stripe gateway is supported."}
            self._save_idempotency_response(
                request, PaymentIdempotency.Action.CREATE, payload, status.HTTP_400_BAD_REQUEST
            )
            return Response(payload, status=status.HTTP_400_BAD_REQUEST)

        stripe_service = StripePaymentService()
        intent = stripe_service.create_payment_intent(
            amount=int(Decimal(data["amount"]) * 100),
            currency=data["currency"].lower(),
            metadata={"order_id": str(order.id), "user_id": request.user.id},
        )
        with transaction.atomic():
            payment = Payment.objects.create(
                order=order,
                amount=data["amount"],
                currency=data["currency"].upper(),
                method=data["method"],
                gateway=data["gateway"],
                gateway_order_id=intent["id"],
                gateway_payment_id=intent["id"],
                gateway_response=intent,
            )

        payload = PaymentSerializer(payment).data
        self._save_idempotency_response(request, PaymentIdempotency.Action.CREATE, payload, status.HTTP_201_CREATED)
        return Response(payload, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=["post"], url_path="verify")
    def verify_payment(self, request):
        if idempotent_response := self._get_idempotency_response(request, PaymentIdempotency.Action.VERIFY):
            return idempotent_response

        serializer = VerifyPaymentRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        payment = Payment.objects.filter(id=data["payment_id"], order__user=request.user).first()
        if not payment:
            payload = {"detail": "Payment not found."}
            self._save_idempotency_response(request, PaymentIdempotency.Action.VERIFY, payload, status.HTTP_404_NOT_FOUND)
            return Response(payload, status=status.HTTP_404_NOT_FOUND)

        payment_intent_id = data.get("gateway_payment_id") or payment.gateway_payment_id
        stripe_service = StripePaymentService()
        intent = stripe_service.retrieve_payment_intent(payment_intent_id)

        self._apply_payment_status(payment, intent.get("status"), dict(intent))

        payload = PaymentSerializer(payment).data
        self._save_idempotency_response(request, PaymentIdempotency.Action.VERIFY, payload, status.HTTP_200_OK)
        return Response(payload, status=status.HTTP_200_OK)

    @action(detail=False, methods=["post"], url_path="webhook", permission_classes=[permissions.AllowAny])
    def gateway_webhook(self, request):
        signature = request.headers.get("Stripe-Signature")
        if not signature:
            return Response({"detail": "Missing Stripe-Signature header."}, status=status.HTTP_400_BAD_REQUEST)

        stripe_service = StripePaymentService()
        try:
            event = stripe_service.construct_event(request.body, signature)
        except Exception:
            return Response({"detail": "Invalid webhook signature."}, status=status.HTTP_400_BAD_REQUEST)

        if PaymentWebhookEvent.objects.filter(event_id=event["id"]).exists():
            return Response({"duplicate": True}, status=status.HTTP_200_OK)

        event_type = event["type"]
        event_object = event["data"]["object"]
        payment = Payment.objects.filter(gateway_payment_id=event_object.get("id")).first()

        if payment and event_type in {
            "payment_intent.succeeded",
            "payment_intent.payment_failed",
            "payment_intent.processing",
            "payment_intent.requires_capture",
        }:
            self._apply_payment_status(payment, event_object.get("status"), event_object)

        PaymentWebhookEvent.objects.create(
            gateway=Payment.Gateway.STRIPE,
            event_id=event["id"],
            event_type=event_type,
            payload=event,
            payment=payment,
        )
        return Response({"received": True}, status=status.HTTP_200_OK)


class RefundViewSet(viewsets.ModelViewSet):
    queryset = Refund.objects.all()
    serializer_class = RefundSerializer
    permission_classes = [permissions.IsAuthenticated]

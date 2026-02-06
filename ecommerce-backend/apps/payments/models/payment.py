import hashid_field
from django.core.exceptions import ValidationError
from django.db import models

from apps.orders.models import Order
from common.models import TimestampedMixin


class Payment(TimestampedMixin, models.Model):
    id = hashid_field.HashidAutoField(primary_key=True)
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="payments")
    gateway_order_id = models.CharField(max_length=255, blank=True)
    gateway_payment_id = models.CharField(max_length=255, blank=True)

    class Gateway(models.TextChoices):
        STRIPE = "stripe", "Stripe"
        RAZORPAY = "razorpay", "Razorpay"
        PAYPAL = "paypal", "PayPal"
        COD = "cod", "Cash on Delivery"

    gateway: models.CharField = models.CharField(max_length=20, choices=Gateway.choices)

    class Method(models.TextChoices):
        CARD = "card", "Card"
        UPI = "upi", "UPI"
        NETBANKING = "netbanking", "Netbanking"
        WALLET = "wallet", "Wallet"
        COD = "cod", "Cash"

    method: models.CharField = models.CharField(max_length=20, choices=Method.choices)

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        AUTHORIZED = "authorized", "Authorized"
        CAPTURED = "captured", "Captured"
        FAILED = "failed", "Failed"
        REFUNDED = "refunded", "Refunded"

    status: models.CharField = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)

    VALID_TRANSITIONS = {
        Status.PENDING: {Status.AUTHORIZED, Status.FAILED},
        Status.AUTHORIZED: {Status.CAPTURED, Status.FAILED, Status.REFUNDED},  # Refunded here acts as Void
        Status.CAPTURED: {Status.REFUNDED},
        Status.FAILED: set(),
        Status.REFUNDED: set(),
    }

    def can_transition_to(self, new_status: str) -> bool:
        if self.status == new_status:
            return True
        return new_status in self.VALID_TRANSITIONS.get(self.status, set())

    amount = models.DecimalField(max_digits=12, decimal_places=2)
    currency = models.CharField(max_length=3, default="USD")
    gateway_response = models.JSONField(default=dict, blank=True)
    failure_reason = models.TextField(blank=True)

    authorized_at = models.DateTimeField(null=True, blank=True)
    captured_at = models.DateTimeField(null=True, blank=True)

    def save(self, *args, **kwargs):
        if self.pk:
            old_instance = Payment.objects.get(pk=self.pk)
            if old_instance.status != self.status and not self.can_transition_to(self.status):
                raise ValidationError(f"Invalid transition from {old_instance.status} to {self.status}")
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.gateway_payment_id} for {self.order.order_number}"

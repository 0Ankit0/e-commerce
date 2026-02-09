import hashid_field
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models

from apps.users.models import Address
from common.models import TimestampedMixin


class Order(TimestampedMixin, models.Model):
    id = hashid_field.HashidAutoField(primary_key=True)
    order_number: models.CharField = models.CharField(max_length=20, unique=True)
    idempotency_key = models.UUIDField(null=True, blank=True)
    user: models.ForeignKey = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="orders"
    )
    address: models.ForeignKey = models.ForeignKey(Address, on_delete=models.PROTECT)

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        CONFIRMED = "confirmed", "Confirmed"
        PROCESSING = "processing", "Processing"
        PACKED = "packed", "Packed"
        SHIPPED = "shipped", "Shipped"
        IN_TRANSIT = "in_transit", "In Transit"
        OUT_FOR_DELIVERY = "out_for_delivery", "Out for Delivery"
        DELIVERED = "delivered", "Delivered"
        CANCELLED = "cancelled", "Cancelled"
        RETURN_REQUESTED = "return_requested", "Return Requested"
        RETURNED = "returned", "Returned"

    status: models.CharField = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)

    VALID_TRANSITIONS = {
        Status.PENDING: {Status.CONFIRMED, Status.CANCELLED},
        Status.CONFIRMED: {Status.PROCESSING, Status.CANCELLED},
        Status.PROCESSING: {Status.PACKED, Status.CANCELLED},
        Status.PACKED: {Status.SHIPPED, Status.CANCELLED},
        Status.SHIPPED: {
            Status.IN_TRANSIT,
            Status.DELIVERED,
            Status.RETURN_REQUESTED,
            Status.RETURNED,
            Status.CANCELLED,
        },
        Status.IN_TRANSIT: {
            Status.OUT_FOR_DELIVERY,
            Status.DELIVERED,
            Status.RETURN_REQUESTED,
            Status.RETURNED,
            Status.CANCELLED,
        },  # Added intermediate states
        Status.OUT_FOR_DELIVERY: {
            Status.DELIVERED,
            Status.RETURN_REQUESTED,
            Status.RETURNED,
            Status.CANCELLED,
        },  # Added intermediate states
        Status.DELIVERED: {Status.RETURN_REQUESTED, Status.RETURNED},
        Status.RETURN_REQUESTED: {Status.RETURNED, Status.CANCELLED},  # Can be cancelled return?
        Status.CANCELLED: set(),
        Status.RETURNED: set(),
    }

    def can_transition_to(self, new_status: str) -> bool:
        if self.status == new_status:
            return True
        return new_status in self.VALID_TRANSITIONS.get(self.status, set())

    class PaymentMethodChoices(models.TextChoices):
        CARD = "card", "Card"
        UPI = "upi", "UPI"
        NETBANKING = "netbanking", "Net Banking"
        WALLET = "wallet", "Wallet"
        COD = "cod", "Cash on Delivery"

    payment_method: models.CharField = models.CharField(max_length=20, choices=PaymentMethodChoices.choices)

    coupon = models.ForeignKey("Coupon", on_delete=models.SET_NULL, null=True, blank=True, related_name="orders")
    coupon_code = models.CharField(max_length=50, blank=True, null=True)
    coupon_discount = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    ip_address = models.GenericIPAddressField(blank=True, null=True)

    class PaymentStatusChoices(models.TextChoices):
        PENDING = "pending", "Pending"
        AUTHORIZED = "authorized", "Authorized"
        CAPTURED = "captured", "Captured"
        FAILED = "failed", "Failed"
        REFUNDED = "refunded", "Refunded"

    payment_status: models.CharField = models.CharField(
        max_length=20, choices=PaymentStatusChoices.choices, default=PaymentStatusChoices.PENDING
    )

    subtotal: models.DecimalField = models.DecimalField(max_digits=12, decimal_places=2)
    discount: models.DecimalField = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    shipping_charge: models.DecimalField = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    tax: models.DecimalField = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total: models.DecimalField = models.DecimalField(max_digits=12, decimal_places=2)

    notes: models.TextField = models.TextField(blank=True)

    confirmed_at: models.DateTimeField = models.DateTimeField(null=True, blank=True)
    shipped_at: models.DateTimeField = models.DateTimeField(null=True, blank=True)
    delivered_at: models.DateTimeField = models.DateTimeField(null=True, blank=True)
    cancelled_at: models.DateTimeField = models.DateTimeField(null=True, blank=True)

    def save(self, *args, **kwargs):
        if self.pk:
            old_instance = Order.objects.get(pk=self.pk)
            if old_instance.status != self.status and not self.can_transition_to(self.status):
                raise ValidationError(f"Invalid transition from {old_instance.status} to {self.status}")
        super().save(*args, **kwargs)

    def __str__(self):
        return self.order_number

    class Meta:
        indexes = [
            models.Index(fields=["user", "created_at"]),
            models.Index(fields=["status"]),
            # models.Index(fields=["created_at"], order="DESC"), # Django 5+ syntax or simplified
            models.Index(fields=["-created_at"], name="idx_orders_created"),
            models.Index(fields=["order_number"]),
            models.Index(fields=["user", "idempotency_key"], name="idx_orders_user_idempotency"),
        ]

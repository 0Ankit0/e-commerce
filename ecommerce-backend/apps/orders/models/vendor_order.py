import hashid_field
from django.core.exceptions import ValidationError
from django.db import models

from apps.vendors.models import Vendor
from common.models import TimestampedMixin

from .order import Order


class VendorOrder(TimestampedMixin, models.Model):
    id = hashid_field.HashidAutoField(primary_key=True)
    order: models.ForeignKey = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="vendor_orders")
    vendor: models.ForeignKey = models.ForeignKey(Vendor, on_delete=models.PROTECT, related_name="vendor_orders")
    vendor_order_number: models.CharField = models.CharField(max_length=50, unique=True)

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        ACCEPTED = "accepted", "Accepted"
        PACKED = "packed", "Packed"
        SHIPPED = "shipped", "Shipped"
        DELIVERED = "delivered", "Delivered"
        CANCELLED = "cancelled", "Cancelled"

    status: models.CharField = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)

    VALID_TRANSITIONS = {
        Status.PENDING: {Status.ACCEPTED, Status.CANCELLED},
        Status.ACCEPTED: {Status.PACKED, Status.CANCELLED},
        Status.PACKED: {Status.SHIPPED, Status.CANCELLED},
        Status.SHIPPED: {Status.DELIVERED},
        Status.DELIVERED: set(),
        Status.CANCELLED: set(),
    }

    def can_transition_to(self, new_status: str) -> bool:
        if self.status == new_status:
            return True
        return new_status in self.VALID_TRANSITIONS.get(self.status, set())

    subtotal: models.DecimalField = models.DecimalField(max_digits=12, decimal_places=2)
    commission: models.DecimalField = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    vendor_amount: models.DecimalField = models.DecimalField(max_digits=12, decimal_places=2)  # subtotal - commission

    accepted_at: models.DateTimeField = models.DateTimeField(null=True, blank=True)
    packed_at: models.DateTimeField = models.DateTimeField(null=True, blank=True)

    def save(self, *args, **kwargs):
        if self.pk:
            old_instance = VendorOrder.objects.get(pk=self.pk)
            if old_instance.status != self.status and not self.can_transition_to(self.status):
                raise ValidationError(f"Invalid transition from {old_instance.status} to {self.status}")
        super().save(*args, **kwargs)

    def __str__(self):
        return self.vendor_order_number

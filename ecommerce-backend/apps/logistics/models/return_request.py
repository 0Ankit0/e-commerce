import hashid_field
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models

from apps.orders.models import Order, OrderItem
from apps.vendors.models import Vendor
from common.models import TimestampedMixin

from .shipment import Shipment


class Return(TimestampedMixin, models.Model):
    id = hashid_field.HashidAutoField(primary_key=True)
    return_number = models.CharField(max_length=50, unique=True)
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="returns")
    order_item = models.ForeignKey(OrderItem, on_delete=models.CASCADE)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="returns")
    vendor = models.ForeignKey(Vendor, on_delete=models.PROTECT)

    class Status(models.TextChoices):
        REQUESTED = "requested", "Requested"
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"
        PICKED_UP = "picked_up", "Picked Up"
        RECEIVED = "received", "Received"
        REFUND_PROCESSED = "refund_processed", "Refund Processed"
        COMPLETED = "completed", "Completed"
        CANCELLED = "cancelled", "Cancelled"

    status: models.CharField = models.CharField(max_length=30, choices=Status.choices, default=Status.REQUESTED)

    VALID_TRANSITIONS = {
        Status.REQUESTED: {Status.APPROVED, Status.REJECTED, Status.CANCELLED},
        Status.APPROVED: {Status.PICKED_UP, Status.CANCELLED},
        Status.REJECTED: set(),  # Final
        Status.PICKED_UP: {Status.RECEIVED},
        Status.RECEIVED: {Status.REFUND_PROCESSED},
        Status.REFUND_PROCESSED: {Status.COMPLETED},
        Status.COMPLETED: set(),  # Final
        Status.CANCELLED: set(),  # Final
    }

    def can_transition_to(self, new_status: str) -> bool:
        if self.status == new_status:
            return True
        return new_status in self.VALID_TRANSITIONS.get(self.status, set())

    class Reason(models.TextChoices):
        DEFECTIVE = "defective", "Defective"
        WRONG_ITEM = "wrong_item", "Wrong Item"
        NOT_SATISFIED = "not_satisfied", "Not Satisfied"
        SIZE_ISSUE = "size_issue", "Size Issue"
        OTHER = "other", "Other"

    reason: models.CharField = models.CharField(max_length=30, choices=Reason.choices)
    reason_text = models.TextField(blank=True)
    images = models.JSONField(default=list, blank=True)

    refund_amount = models.DecimalField(max_digits=12, decimal_places=2)

    reverse_shipment = models.OneToOneField(
        Shipment, on_delete=models.SET_NULL, null=True, blank=True, related_name="return_request"
    )

    approved_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    def save(self, *args, **kwargs):
        if self.pk:
            old_instance = Return.objects.get(pk=self.pk)
            if old_instance.status != self.status and not self.can_transition_to(self.status):
                raise ValidationError(f"Invalid transition from {old_instance.status} to {self.status}")
        super().save(*args, **kwargs)

    def __str__(self):
        return self.return_number

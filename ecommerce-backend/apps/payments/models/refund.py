import hashid_field
from django.core.exceptions import ValidationError
from django.db import models

from common.models import TimestampedMixin

from .payment import Payment


class Refund(TimestampedMixin, models.Model):
    id = hashid_field.HashidAutoField(primary_key=True)
    payment = models.ForeignKey(Payment, on_delete=models.CASCADE, related_name="refunds")
    # Link to Return if needed, but Return is in logistics, circle dep potential.
    # String ref 'logistics.Return'

    gateway_refund_id = models.CharField(max_length=255, blank=True)
    amount = models.DecimalField(max_digits=12, decimal_places=2)

    class Reason(models.TextChoices):
        RETURN = "return", "Return"
        CANCELLATION = "cancellation", "Cancellation"
        OTHER = "other", "Other"

    reason: models.CharField = models.CharField(max_length=20, choices=Reason.choices)

    class Status(models.TextChoices):
        INITIATED = "initiated", "Initiated"
        PROCESSED = "processed", "Processed"
        FAILED = "failed", "Failed"

    status: models.CharField = models.CharField(max_length=20, choices=Status.choices, default=Status.INITIATED)

    VALID_TRANSITIONS = {
        Status.INITIATED: {Status.PROCESSED, Status.FAILED},
        Status.PROCESSED: set(),
        Status.FAILED: {Status.INITIATED},  # Retry
    }

    def can_transition_to(self, new_status: str) -> bool:
        if self.status == new_status:
            return True
        return new_status in self.VALID_TRANSITIONS.get(self.status, set())

    class Method(models.TextChoices):
        ORIGINAL = "original", "Original Source"
        WALLET = "wallet", "Wallet"

    method: models.CharField = models.CharField(max_length=20, choices=Method.choices, default=Method.ORIGINAL)

    gateway_response = models.JSONField(default=dict, blank=True)
    processed_at = models.DateTimeField(null=True, blank=True)

    def save(self, *args, **kwargs):
        if self.pk:
            old_instance = Refund.objects.get(pk=self.pk)
            if old_instance.status != self.status and not self.can_transition_to(self.status):
                raise ValidationError(f"Invalid transition from {old_instance.status} to {self.status}")
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Refund {self.id} for {self.payment}"

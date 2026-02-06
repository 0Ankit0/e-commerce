import hashid_field
from django.core.exceptions import ValidationError
from django.db import models

from common.models import TimestampedMixin

from .vendor import Vendor


class BankAccount(TimestampedMixin, models.Model):
    id = hashid_field.HashidAutoField(primary_key=True)
    vendor = models.ForeignKey(Vendor, on_delete=models.CASCADE, related_name="bank_accounts")
    account_name = models.CharField(max_length=255)
    account_number = models.CharField(max_length=50)
    ifsc_code = models.CharField(max_length=20)
    bank_name = models.CharField(max_length=100)
    is_primary = models.BooleanField(default=False)

    class VerificationStatus(models.TextChoices):
        PENDING = "pending", "Pending"
        VERIFIED = "verified", "Verified"
        FAILED = "failed", "Failed"

    verification_status: models.CharField = models.CharField(
        max_length=20, choices=VerificationStatus.choices, default=VerificationStatus.PENDING
    )

    VALID_TRANSITIONS = {
        VerificationStatus.PENDING: {VerificationStatus.VERIFIED, VerificationStatus.FAILED},
        VerificationStatus.VERIFIED: {VerificationStatus.FAILED},  # If verification revoked
        VerificationStatus.FAILED: {VerificationStatus.PENDING},  # Retry
    }

    def can_transition_to(self, new_status: str) -> bool:
        if self.verification_status == new_status:
            return True
        return new_status in self.VALID_TRANSITIONS.get(self.verification_status, set())

    def __str__(self):
        return f"{self.bank_name} - {self.account_number}"

    def save(self, *args, **kwargs):
        if self.pk:
            old_instance = BankAccount.objects.get(pk=self.pk)
            if old_instance.verification_status != self.verification_status and not self.can_transition_to(
                self.verification_status
            ):
                raise ValidationError(
                    f"Invalid transition from {old_instance.verification_status} to {self.verification_status}"
                )

        if self.is_primary:
            BankAccount.objects.filter(vendor=self.vendor).exclude(id=self.id).update(is_primary=False)
        super().save(*args, **kwargs)

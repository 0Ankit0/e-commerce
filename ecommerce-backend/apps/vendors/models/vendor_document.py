import hashid_field
from django.core.exceptions import ValidationError
from django.db import models

from common.models import TimestampedMixin
from common.storages import PublicS3Boto3StorageWithCDN, UniqueFilePathGenerator

from .vendor import Vendor


class VendorDocument(TimestampedMixin, models.Model):
    id = hashid_field.HashidAutoField(primary_key=True)
    vendor = models.ForeignKey(Vendor, on_delete=models.CASCADE, related_name="documents")

    class DocType(models.TextChoices):
        GST = "gst", "GST Certificate"
        PAN = "pan", "PAN Card"
        CANCEL_CHEQUE = "cancel_cheque", "Cancelled Cheque"
        OTHER = "other", "Other"

    doc_type: models.CharField = models.CharField(max_length=50, choices=DocType.choices)
    doc_number = models.CharField(max_length=100, blank=True)
    file = models.FileField(storage=PublicS3Boto3StorageWithCDN, upload_to=UniqueFilePathGenerator("vendors/documents"))

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        VERIFIED = "verified", "Verified"
        REJECTED = "rejected", "Rejected"

    status: models.CharField = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)

    VALID_TRANSITIONS = {
        Status.PENDING: {Status.VERIFIED, Status.REJECTED},
        Status.VERIFIED: {Status.REJECTED},  # In case of audit failure
        Status.REJECTED: {Status.PENDING},  # Re-upload
    }

    def can_transition_to(self, new_status: str) -> bool:
        if self.status == new_status:
            return True
        return new_status in self.VALID_TRANSITIONS.get(self.status, set())

    remarks = models.TextField(blank=True)
    verified_at = models.DateTimeField(null=True, blank=True)

    def save(self, *args, **kwargs):
        if self.pk:
            old_instance = VendorDocument.objects.get(pk=self.pk)
            if old_instance.status != self.status and not self.can_transition_to(self.status):
                raise ValidationError(f"Invalid transition from {old_instance.status} to {self.status}")
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.vendor.business_name} - {self.doc_type}"

import hashid_field
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils.text import slugify

from common.models import TimestampedMixin
from common.storages import PublicS3Boto3StorageWithCDN, UniqueFilePathGenerator


class Vendor(TimestampedMixin, models.Model):
    id = hashid_field.HashidAutoField(primary_key=True)
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="vendor_profile")
    business_name = models.CharField(max_length=255)
    display_name = models.CharField(max_length=255)
    slug = models.SlugField(max_length=255, unique=True, blank=True)
    description = models.TextField(blank=True)

    logo = models.ImageField(
        storage=PublicS3Boto3StorageWithCDN, upload_to=UniqueFilePathGenerator("vendors/logos"), null=True, blank=True
    )
    banner = models.ImageField(
        storage=PublicS3Boto3StorageWithCDN, upload_to=UniqueFilePathGenerator("vendors/banners"), null=True, blank=True
    )

    gstin = models.CharField(max_length=50, blank=True)
    pan = models.CharField(max_length=50, blank=True)

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"
        SUSPENDED = "suspended", "Suspended"

    status: models.CharField = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)

    VALID_TRANSITIONS = {
        Status.PENDING: {Status.APPROVED, Status.REJECTED},
        Status.APPROVED: {Status.SUSPENDED},
        Status.SUSPENDED: {Status.APPROVED},
        Status.REJECTED: {Status.PENDING},  # Allow re-application
    }

    def can_transition_to(self, new_status: str) -> bool:
        if self.status == new_status:
            return True
        return new_status in self.VALID_TRANSITIONS.get(self.status, set())

    rating = models.DecimalField(max_digits=3, decimal_places=2, default=0)
    rating_count = models.PositiveIntegerField(default=0)
    product_count = models.PositiveIntegerField(default=0)

    class CommissionTier(models.TextChoices):
        STANDARD = "standard", "Standard"
        GOLD = "gold", "Gold"
        PLATINUM = "platinum", "Platinum"

    commission_tier: models.CharField = models.CharField(
        max_length=20, choices=CommissionTier.choices, default=CommissionTier.STANDARD
    )

    approved_at = models.DateTimeField(null=True, blank=True)

    def save(self, *args, **kwargs):
        if self.pk:
            old_instance = Vendor.objects.get(pk=self.pk)
            if old_instance.status != self.status and not self.can_transition_to(self.status):
                raise ValidationError(f"Invalid transition from {old_instance.status} to {self.status}")

        if not self.slug:
            self.slug = slugify(self.business_name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.business_name

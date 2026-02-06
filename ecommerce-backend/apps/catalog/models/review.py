import hashid_field
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models

from common.models import TimestampedMixin

from .product import Product


class Review(TimestampedMixin, models.Model):
    id = hashid_field.HashidAutoField(primary_key=True)
    product: models.ForeignKey = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="reviews")
    user: models.ForeignKey = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="reviews"
    )
    # Using string reference for Order to avoid potential circular/import issues if not strictly necessary here,
    # but based on previous models.py it was imported.
    # Let's use string reference 'orders.Order' which Django supports.
    order = models.ForeignKey("orders.Order", on_delete=models.SET_NULL, null=True, blank=True, related_name="reviews")

    rating: models.PositiveIntegerField = models.PositiveIntegerField()
    title: models.CharField = models.CharField(max_length=255, blank=True)
    content: models.TextField = models.TextField()
    images: models.JSONField = models.JSONField(default=list, blank=True)  # List of URLs

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"

    status: models.CharField = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)

    VALID_TRANSITIONS = {
        Status.PENDING: {Status.APPROVED, Status.REJECTED},
        Status.APPROVED: {Status.REJECTED},  # Moderator checks again
        Status.REJECTED: {Status.APPROVED},  # Appeal/Fix
    }

    def can_transition_to(self, new_status: str) -> bool:
        if self.status == new_status:
            return True
        return new_status in self.VALID_TRANSITIONS.get(self.status, set())

    def save(self, *args, **kwargs):
        if self.pk:
            old_instance = Review.objects.get(pk=self.pk)
            if old_instance.status != self.status and not self.can_transition_to(self.status):
                raise ValidationError(f"Invalid transition from {old_instance.status} to {self.status}")
        super().save(*args, **kwargs)

    helpful_count: models.PositiveIntegerField = models.PositiveIntegerField(default=0)

    def __str__(self):
        return f"{self.rating} star review by {self.user}"

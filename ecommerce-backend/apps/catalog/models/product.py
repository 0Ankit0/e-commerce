import hashid_field
from django.core.exceptions import ValidationError
from django.db import models
from django.utils.text import slugify

from apps.vendors.models import Vendor
from common.models import TimestampedMixin

from .brand import Brand
from .category import Category


class Product(TimestampedMixin, models.Model):
    id = hashid_field.HashidAutoField(primary_key=True)
    vendor = models.ForeignKey(Vendor, on_delete=models.CASCADE, related_name="products")
    category = models.ForeignKey(Category, on_delete=models.PROTECT, related_name="products")
    brand = models.ForeignKey(Brand, on_delete=models.SET_NULL, null=True, blank=True, related_name="products")
    name = models.CharField(max_length=255)
    slug = models.SlugField(max_length=300, unique=True)
    short_description = models.TextField(blank=True)
    description = models.TextField(blank=True)
    specifications = models.JSONField(default=dict, blank=True)

    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        PENDING = "pending", "Pending Approval"
        ACTIVE = "active", "Active"
        INACTIVE = "inactive", "Inactive"
        DELETED = "deleted", "Deleted"

    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT)

    VALID_TRANSITIONS = {
        Status.DRAFT: {Status.PENDING, Status.DELETED},
        Status.PENDING: {Status.ACTIVE, Status.INACTIVE, Status.DRAFT, Status.DELETED},
        Status.ACTIVE: {Status.INACTIVE, Status.DELETED},
        Status.INACTIVE: {Status.ACTIVE, Status.DELETED},
        Status.DELETED: set(),
    }

    def can_transition_to(self, new_status: str) -> bool:
        if self.status == new_status:
            return True
        return new_status in self.VALID_TRANSITIONS.get(self.Status(self.status), set())

    avg_rating = models.DecimalField(max_digits=3, decimal_places=2, default=0)
    review_count = models.PositiveIntegerField(default=0)
    view_count = models.PositiveIntegerField(default=0)
    is_featured = models.BooleanField(default=False)
    seo_data = models.JSONField(default=dict, blank=True)
    published_at = models.DateTimeField(null=True, blank=True)

    def save(self, *args, **kwargs):
        if self.pk:
            old_instance = Product.objects.get(pk=self.pk)
            if old_instance.status != self.status and not self.can_transition_to(self.status):
                raise ValidationError(f"Invalid transition from {old_instance.status} to {self.status}")

        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name

    class Meta:
        indexes = [
            models.Index(fields=["vendor"]),
            models.Index(fields=["category"]),
            models.Index(fields=["status"]),
            models.Index(fields=["is_featured"], condition=models.Q(is_featured=True), name="idx_products_featured"),
            # GIN index for search would require contrib.postgres and additional setup, skipping for now or adding standard index?
            # Standard Django doesn't support functional indexes easily without specific DB backends.
            # I will add a standard index on name and slug.
            models.Index(fields=["name"]),
            models.Index(fields=["slug"]),
        ]

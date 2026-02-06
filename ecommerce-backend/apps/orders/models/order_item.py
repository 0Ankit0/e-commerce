import hashid_field
from django.core.exceptions import ValidationError
from django.db import models

from apps.catalog.models import Product, ProductVariant
from apps.vendors.models import Vendor
from common.models import TimestampedMixin

from .order import Order
from .vendor_order import VendorOrder


class OrderItem(TimestampedMixin, models.Model):
    id = hashid_field.HashidAutoField(primary_key=True)
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items")
    vendor_order = models.ForeignKey(VendorOrder, on_delete=models.CASCADE, related_name="items", null=True)

    vendor = models.ForeignKey(Vendor, on_delete=models.PROTECT)
    product = models.ForeignKey(Product, on_delete=models.PROTECT)
    variant = models.ForeignKey(ProductVariant, on_delete=models.PROTECT)

    product_name: models.CharField = models.CharField(max_length=255)
    variant_name: models.CharField = models.CharField(max_length=255)
    image_url: models.CharField = models.CharField(max_length=500, blank=True)

    quantity: models.PositiveIntegerField = models.PositiveIntegerField()
    unit_price: models.DecimalField = models.DecimalField(max_digits=10, decimal_places=2)
    total_price: models.DecimalField = models.DecimalField(max_digits=10, decimal_places=2)

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        CONFIRMED = "confirmed", "Confirmed"
        SHIPPED = "shipped", "Shipped"
        DELIVERED = "delivered", "Delivered"
        CANCELLED = "cancelled", "Cancelled"
        RETURNED = "returned", "Returned"

    status: models.CharField = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)

    VALID_TRANSITIONS = {
        Status.PENDING: {Status.CONFIRMED, Status.CANCELLED},
        Status.CONFIRMED: {Status.SHIPPED, Status.CANCELLED},
        Status.SHIPPED: {Status.DELIVERED, Status.RETURNED},  # Returned if rejected at door
        Status.DELIVERED: {Status.RETURNED},
        Status.CANCELLED: set(),
        Status.RETURNED: set(),
    }

    def can_transition_to(self, new_status: str) -> bool:
        if self.status == new_status:
            return True
        return new_status in self.VALID_TRANSITIONS.get(self.status, set())

    def save(self, *args, **kwargs):
        if self.pk:
            old_instance = OrderItem.objects.get(pk=self.pk)
            if old_instance.status != self.status and not self.can_transition_to(self.status):
                raise ValidationError(f"Invalid transition from {old_instance.status} to {self.status}")
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.quantity} x {self.product_name} in {self.order.order_number}"

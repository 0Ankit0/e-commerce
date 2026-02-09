import hashid_field
from django.db import models
from django.utils import timezone

from common.models import TimestampedMixin


class Coupon(TimestampedMixin, models.Model):
    id = hashid_field.HashidAutoField(primary_key=True)
    code = models.CharField(max_length=50, unique=True)
    description = models.TextField(blank=True)

    class DiscountType(models.TextChoices):
        PERCENTAGE = "percentage", "Percentage"
        FIXED = "fixed", "Fixed Amount"

    discount_type = models.CharField(max_length=20, choices=DiscountType.choices, default=DiscountType.PERCENTAGE)
    discount_value = models.DecimalField(max_digits=10, decimal_places=2)

    min_order_value = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    max_discount_amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)

    start_date = models.DateTimeField(default=timezone.now)
    end_date = models.DateTimeField(null=True, blank=True)

    usage_limit = models.PositiveIntegerField(null=True, blank=True)
    usage_count = models.PositiveIntegerField(default=0)

    is_active = models.BooleanField(default=True)

    def is_valid(self):
        now = timezone.now()
        if not self.is_active:
            return False
        if self.end_date and now > self.end_date:
            return False
        if self.start_date and now < self.start_date:
            return False
        if self.usage_limit and self.usage_count >= self.usage_limit:
            return False
        return True

    def __str__(self):
        return self.code

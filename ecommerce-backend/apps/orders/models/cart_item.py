import hashid_field
from django.db import models

from apps.catalog.models import ProductVariant
from common.models import TimestampedMixin

from .cart import Cart


class CartItem(TimestampedMixin, models.Model):
    id = hashid_field.HashidAutoField(primary_key=True)
    cart: models.ForeignKey = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name="items")
    variant: models.ForeignKey = models.ForeignKey(ProductVariant, on_delete=models.CASCADE)
    quantity: models.PositiveIntegerField = models.PositiveIntegerField(default=1)
    price_at_add: models.DecimalField = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return f"{self.quantity} x {self.variant.name}"

import hashid_field
from django.db import models

from apps.catalog.models import ProductVariant
from common.models import TimestampedMixin

from .warehouse import Warehouse


class Inventory(TimestampedMixin, models.Model):
    id = hashid_field.HashidAutoField(primary_key=True)
    variant = models.ForeignKey(ProductVariant, on_delete=models.CASCADE, related_name="inventory")
    warehouse = models.ForeignKey(Warehouse, on_delete=models.CASCADE, related_name="inventory")
    quantity = models.IntegerField(default=0)
    reserved_qty = models.IntegerField(default=0)
    reorder_level = models.IntegerField(default=10)
    reorder_qty = models.IntegerField(default=50)
    last_restocked_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name_plural = "Inventory"
        unique_together = ("variant", "warehouse")

    def __str__(self):
        return f"{self.variant.sku} in {self.warehouse.name}: {self.quantity}"

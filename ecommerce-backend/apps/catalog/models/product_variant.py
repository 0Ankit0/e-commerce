import hashid_field
from django.db import models
from common.models import TimestampedMixin
from .product import Product

class ProductVariant(TimestampedMixin, models.Model):
    id = hashid_field.HashidAutoField(primary_key=True)
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='variants')
    sku = models.CharField(max_length=100, unique=True)
    name = models.CharField(max_length=255)
    mrp = models.DecimalField(max_digits=10, decimal_places=2)
    selling_price = models.DecimalField(max_digits=10, decimal_places=2)
    cost_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    attributes = models.JSONField(default=dict)
    weight = models.DecimalField(max_digits=10, decimal_places=3, null=True, blank=True) # in kg
    dimensions = models.JSONField(default=dict, blank=True) # l,b,h
    is_default = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.product.name} - {self.name}"

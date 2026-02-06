import hashid_field
from django.db import models
from common.models import TimestampedMixin
from apps.vendors.models import Vendor
from apps.catalog.models import Product, ProductVariant
from .order import Order
from .vendor_order import VendorOrder

class OrderItem(TimestampedMixin, models.Model):
    id = hashid_field.HashidAutoField(primary_key=True)
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    vendor_order = models.ForeignKey(VendorOrder, on_delete=models.CASCADE, related_name='items', null=True)
    
    vendor = models.ForeignKey(Vendor, on_delete=models.PROTECT)
    product = models.ForeignKey(Product, on_delete=models.PROTECT)
    variant = models.ForeignKey(ProductVariant, on_delete=models.PROTECT)
    
    product_name = models.CharField(max_length=255)
    variant_name = models.CharField(max_length=255)
    image_url = models.CharField(max_length=500, blank=True)
    
    quantity = models.PositiveIntegerField()
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    total_price = models.DecimalField(max_digits=10, decimal_places=2)
    
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('confirmed', 'Confirmed'),
        ('shipped', 'Shipped'),
        ('delivered', 'Delivered'),
        ('cancelled', 'Cancelled'),
        ('returned', 'Returned'),
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')

    def __str__(self):
        return f"{self.quantity} x {self.product_name} in {self.order.order_number}"

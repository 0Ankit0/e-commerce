import hashid_field
from django.db import models
from common.models import TimestampedMixin
from apps.vendors.models import Vendor
from .order import Order

class VendorOrder(TimestampedMixin, models.Model):
    id = hashid_field.HashidAutoField(primary_key=True)
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='vendor_orders')
    vendor = models.ForeignKey(Vendor, on_delete=models.PROTECT, related_name='vendor_orders')
    vendor_order_number = models.CharField(max_length=50, unique=True)
    
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('accepted', 'Accepted'),
        ('packed', 'Packed'),
        ('shipped', 'Shipped'),
        ('delivered', 'Delivered'),
        ('cancelled', 'Cancelled'),
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    
    subtotal = models.DecimalField(max_digits=12, decimal_places=2)
    commission = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    vendor_amount = models.DecimalField(max_digits=12, decimal_places=2) # subtotal - commission
    
    accepted_at = models.DateTimeField(null=True, blank=True)
    packed_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return self.vendor_order_number

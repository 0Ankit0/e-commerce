import hashid_field
from django.db import models
from common.models import TimestampedMixin
from apps.orders.models import Order, VendorOrder
from apps.vendors.models import Vendor
from apps.inventory.models import Warehouse
from .branch import Branch
from .delivery_agent import DeliveryAgent

class Shipment(TimestampedMixin, models.Model):
    id = hashid_field.HashidAutoField(primary_key=True)
    awb = models.CharField(max_length=50, unique=True)
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='shipments')
    vendor_order = models.OneToOneField(VendorOrder, on_delete=models.CASCADE, related_name='shipment', null=True, blank=True)
    vendor = models.ForeignKey(Vendor, on_delete=models.PROTECT)
    warehouse = models.ForeignKey(Warehouse, on_delete=models.PROTECT, null=True, blank=True)
    branch = models.ForeignKey(Branch, on_delete=models.PROTECT, null=True, blank=True)
    agent = models.ForeignKey(DeliveryAgent, on_delete=models.PROTECT, null=True, blank=True)
    
    STATUS_CHOICES = (
        ('created', 'Created'),
        ('awaiting_pickup', 'Awaiting Pickup'),
        ('picked_up', 'Picked Up'),
        ('in_transit', 'In Transit'),
        ('at_hub', 'At Hub'),
        ('out_for_delivery', 'Out for Delivery'),
        ('delivered', 'Delivered'),
        ('delivery_failed', 'Delivery Failed'),
        ('rto_initiated', 'RTO Initiated'),
        ('rto_in_transit', 'RTO In Transit'),
        ('rto_delivered', 'RTO Delivered'),
        ('cancelled', 'Cancelled'),
    )
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default='created')
    
    TYPE_CHOICES = (
        ('forward', 'Forward'),
        ('reverse', 'Reverse'),
        ('rto', 'RTO'),
    )
    type = models.CharField(max_length=20, choices=TYPE_CHOICES, default='forward')
    
    weight = models.DecimalField(max_digits=10, decimal_places=3, null=True, blank=True)
    dimensions = models.JSONField(default=dict, blank=True)
    declared_value = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    is_cod = models.BooleanField(default=False)
    cod_amount = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    
    picked_up_at = models.DateTimeField(null=True, blank=True)
    delivered_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return self.awb

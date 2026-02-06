import hashid_field
from django.conf import settings
from django.db import models
from common.models import TimestampedMixin
from apps.orders.models import Order, OrderItem
from apps.vendors.models import Vendor
from .shipment import Shipment

class Return(TimestampedMixin, models.Model):
    id = hashid_field.HashidAutoField(primary_key=True)
    return_number = models.CharField(max_length=50, unique=True)
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='returns')
    order_item = models.ForeignKey(OrderItem, on_delete=models.CASCADE)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='returns')
    vendor = models.ForeignKey(Vendor, on_delete=models.PROTECT)
    
    STATUS_CHOICES = (
        ('requested', 'Requested'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('picked_up', 'Picked Up'),
        ('received', 'Received'),
        ('refund_processed', 'Refund Processed'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    )
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default='requested')
    
    REASON_CHOICES = (
        ('defective', 'Defective'),
        ('wrong_item', 'Wrong Item'),
        ('not_satisfied', 'Not Satisfied'),
        ('size_issue', 'Size Issue'),
        ('other', 'Other'),
    )
    reason = models.CharField(max_length=30, choices=REASON_CHOICES)
    reason_text = models.TextField(blank=True)
    images = models.JSONField(default=list, blank=True)
    
    refund_amount = models.DecimalField(max_digits=12, decimal_places=2)
    
    reverse_shipment = models.OneToOneField(Shipment, on_delete=models.SET_NULL, null=True, blank=True, related_name='return_request')
    
    approved_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return self.return_number

import hashid_field
from django.db import models
from common.models import TimestampedMixin
from .payment import Payment

class Refund(TimestampedMixin, models.Model):
    id = hashid_field.HashidAutoField(primary_key=True)
    payment = models.ForeignKey(Payment, on_delete=models.CASCADE, related_name='refunds')
    # Link to Return if needed, but Return is in logistics, circle dep potential.
    # String ref 'logistics.Return'
    
    gateway_refund_id = models.CharField(max_length=255, blank=True)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    
    REASON_CHOICES = (
        ('return', 'Return'),
        ('cancellation', 'Cancellation'),
        ('other', 'Other'),
    )
    reason = models.CharField(max_length=20, choices=REASON_CHOICES)
    
    STATUS_CHOICES = (
        ('initiated', 'Initiated'),
        ('processed', 'Processed'),
        ('failed', 'Failed'),
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='initiated')
    
    METHOD_CHOICES = (
        ('original', 'Original Source'),
        ('wallet', 'Wallet'),
    )
    method = models.CharField(max_length=20, choices=METHOD_CHOICES, default='original')
    
    gateway_response = models.JSONField(default=dict, blank=True)
    processed_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"Refund {self.id} for {self.payment}"

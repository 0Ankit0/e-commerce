import hashid_field
from django.db import models
from common.models import TimestampedMixin
from apps.orders.models import Order

class Payment(TimestampedMixin, models.Model):
    id = hashid_field.HashidAutoField(primary_key=True)
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='payments')
    gateway_order_id = models.CharField(max_length=255, blank=True)
    gateway_payment_id = models.CharField(max_length=255, blank=True)
    
    GATEWAY_CHOICES = (
        ('stripe', 'Stripe'),
        ('razorpay', 'Razorpay'),
        ('paypal', 'PayPal'),
        ('cod', 'Cash on Delivery'),
    )
    gateway = models.CharField(max_length=20, choices=GATEWAY_CHOICES)
    
    METHOD_CHOICES = (
        ('card', 'Card'),
        ('upi', 'UPI'),
        ('netbanking', 'Netbanking'),
        ('wallet', 'Wallet'),
        ('cod', 'Cash'),
    )
    method = models.CharField(max_length=20, choices=METHOD_CHOICES)
    
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('authorized', 'Authorized'),
        ('captured', 'Captured'),
        ('failed', 'Failed'),
        ('refunded', 'Refunded'),
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    currency = models.CharField(max_length=3, default='USD')
    gateway_response = models.JSONField(default=dict, blank=True)
    failure_reason = models.TextField(blank=True)
    
    authorized_at = models.DateTimeField(null=True, blank=True)
    captured_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.gateway_payment_id} for {self.order.order_number}"

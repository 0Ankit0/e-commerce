import hashid_field
from django.conf import settings
from django.db import models
from common.models import TimestampedMixin
from .product import Product

class Review(TimestampedMixin, models.Model):
    id = hashid_field.HashidAutoField(primary_key=True)
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='reviews')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='reviews')
    # Using string reference for Order to avoid potential circular/import issues if not strictly necessary here, 
    # but based on previous models.py it was imported. 
    # Let's use string reference 'orders.Order' which Django supports.
    order = models.ForeignKey('orders.Order', on_delete=models.SET_NULL, null=True, blank=True, related_name='reviews')
    
    rating = models.PositiveIntegerField()
    title = models.CharField(max_length=255, blank=True)
    content = models.TextField()
    images = models.JSONField(default=list, blank=True) # List of URLs
    
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    helpful_count = models.PositiveIntegerField(default=0)

    def __str__(self):
        return f"{self.rating} star review by {self.user}"

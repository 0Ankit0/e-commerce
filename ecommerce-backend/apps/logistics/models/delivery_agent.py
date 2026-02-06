import hashid_field
from django.conf import settings
from django.db import models
from common.models import TimestampedMixin
from .branch import Branch

class DeliveryAgent(TimestampedMixin, models.Model):
    id = hashid_field.HashidAutoField(primary_key=True)
    branch = models.ForeignKey(Branch, on_delete=models.CASCADE, related_name='agents')
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='delivery_profile')
    vehicle_number = models.CharField(max_length=50)
    
    VEHICLE_TYPE_CHOICES = (
        ('bike', 'Bike'),
        ('van', 'Van'),
        ('truck', 'Truck'),
    )
    vehicle_type = models.CharField(max_length=20, choices=VEHICLE_TYPE_CHOICES)
    
    STATUS_CHOICES = (
        ('available', 'Available'),
        ('busy', 'Busy'),
        ('offline', 'Offline'),
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='offline')
    
    capacity = models.IntegerField(default=50)
    current_load = models.IntegerField(default=0)
    current_lat = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    current_lng = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    last_location_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.user.email} ({self.branch.code})"

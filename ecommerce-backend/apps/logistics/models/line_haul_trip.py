import hashid_field
from django.db import models
from common.models import TimestampedMixin
from .hub import Hub

class LineHaulTrip(TimestampedMixin, models.Model):
    id = hashid_field.HashidAutoField(primary_key=True)
    trip_number = models.CharField(max_length=50, unique=True)
    origin_hub = models.ForeignKey(Hub, on_delete=models.CASCADE, related_name='trips_origin')
    dest_hub = models.ForeignKey(Hub, on_delete=models.CASCADE, related_name='trips_dest')
    vehicle_number = models.CharField(max_length=50, blank=True)
    driver_name = models.CharField(max_length=100, blank=True)
    
    STATUS_CHOICES = (
        ('scheduled', 'Scheduled'),
        ('in_transit', 'In Transit'),
        ('arrived', 'Arrived'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='scheduled')
    
    package_count = models.PositiveIntegerField(default=0)
    total_weight = models.DecimalField(max_digits=10, decimal_places=3, default=0)
    
    scheduled_departure = models.DateTimeField(null=True, blank=True)
    actual_departure = models.DateTimeField(null=True, blank=True)
    scheduled_arrival = models.DateTimeField(null=True, blank=True)
    actual_arrival = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return self.trip_number

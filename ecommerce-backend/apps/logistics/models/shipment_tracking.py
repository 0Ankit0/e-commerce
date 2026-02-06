import hashid_field
from django.db import models
from common.models import TimestampedMixin
from .shipment import Shipment

class ShipmentTracking(TimestampedMixin, models.Model):
    id = hashid_field.HashidAutoField(primary_key=True)
    shipment = models.ForeignKey(Shipment, on_delete=models.CASCADE, related_name='tracking_logs')
    status = models.CharField(max_length=50)
    location = models.CharField(max_length=255)
    remarks = models.TextField(blank=True)
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-timestamp']

    def __str__(self):
        return f"{self.shipment.awb} - {self.status}"

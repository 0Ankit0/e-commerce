import hashid_field
from django.db import models

from common.models import TimestampedMixin


class Hub(TimestampedMixin, models.Model):
    id = hashid_field.HashidAutoField(primary_key=True)
    name = models.CharField(max_length=255)
    code = models.CharField(max_length=50, unique=True)

    class Type(models.TextChoices):
        ORIGIN = "origin", "Origin"
        TRANSIT = "transit", "Transit"
        DESTINATION = "destination", "Destination"

    type: models.CharField = models.CharField(max_length=20, choices=Type.choices)

    address = models.CharField(max_length=500)
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100)
    pincode = models.CharField(max_length=20)
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    contact_phone = models.CharField(max_length=20)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.name} ({self.code})"

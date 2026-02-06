import hashid_field
from django.db import models
from common.models import TimestampedMixin
from .hub import Hub

class Branch(TimestampedMixin, models.Model):
    id = hashid_field.HashidAutoField(primary_key=True)
    hub = models.ForeignKey(Hub, on_delete=models.CASCADE, related_name='branches')
    name = models.CharField(max_length=255)
    code = models.CharField(max_length=50, unique=True)
    address = models.CharField(max_length=500)
    service_pincodes = models.JSONField(default=list) # List of pincodes
    contact_phone = models.CharField(max_length=20)
    agent_capacity = models.PositiveIntegerField(default=10)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.name} ({self.code})"

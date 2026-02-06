import hashid_field
from django.conf import settings
from django.db import models
from common.models import TimestampedMixin

class Cart(TimestampedMixin, models.Model):
    id = hashid_field.HashidAutoField(primary_key=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='carts')
    session_id = models.CharField(max_length=255, blank=True)
    
    def __str__(self):
        return f"Cart {self.id} for {self.user}"

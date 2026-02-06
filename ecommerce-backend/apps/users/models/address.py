import hashid_field
from django.db import models

from common.models import TimestampedMixin

from .user import User


class Address(TimestampedMixin, models.Model):
    id = hashid_field.HashidAutoField(primary_key=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="addresses")
    name = models.CharField(max_length=255)
    phone = models.CharField(max_length=20)
    line1 = models.CharField(max_length=255)
    line2 = models.CharField(max_length=255, blank=True)
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100)
    pincode = models.CharField(max_length=20)
    country = models.CharField(max_length=100)
    landmark = models.CharField(max_length=255, blank=True)
    type = models.CharField(
        max_length=20, choices=[("home", "Home"), ("work", "Work"), ("other", "Other")], default="home"
    )
    is_default = models.BooleanField(default=False)
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)

    def save(self, *args, **kwargs):
        if self.is_default:
            Address.objects.filter(user=self.user).exclude(id=self.id).update(is_default=False)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.name}, {self.city}"

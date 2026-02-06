from typing import TYPE_CHECKING

import hashid_field
from django.conf import settings
from django.db import models

from common.models import TimestampedMixin

if TYPE_CHECKING:
    from .cart_item import CartItem


class Cart(TimestampedMixin, models.Model):
    id = hashid_field.HashidAutoField(primary_key=True)
    user: models.ForeignKey = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="carts"
    )
    session_id: models.CharField = models.CharField(max_length=255, blank=True)

    if TYPE_CHECKING:
        items: models.QuerySet["CartItem"]

    def __str__(self):
        return f"Cart {self.id} for {self.user}"

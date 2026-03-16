from django.conf import settings
from django.db import models

from apps.catalog.models import Product
from common.models import TimestampedMixin


class RecommendationEvent(TimestampedMixin, models.Model):
    class EventType(models.TextChoices):
        VIEW = "view", "View"
        CLICK = "click", "Click"
        CART = "cart", "Cart"
        WISHLIST = "wishlist", "Wishlist"
        PURCHASE = "purchase", "Purchase"

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="recommendation_events")
    event_type = models.CharField(max_length=20, choices=EventType.choices)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=["event_type", "created_at"]),
            models.Index(fields=["product", "created_at"]),
            models.Index(fields=["user", "created_at"]),
        ]

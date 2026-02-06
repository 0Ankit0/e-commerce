import hashid_field
from django.core.exceptions import ValidationError
from django.db import models

from apps.inventory.models import Warehouse
from apps.orders.models import Order, VendorOrder
from apps.vendors.models import Vendor
from common.models import TimestampedMixin

from .branch import Branch
from .delivery_agent import DeliveryAgent


class Shipment(TimestampedMixin, models.Model):
    id = hashid_field.HashidAutoField(primary_key=True)
    awb = models.CharField(max_length=50, unique=True)
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="shipments")
    vendor_order = models.OneToOneField(
        VendorOrder, on_delete=models.CASCADE, related_name="shipment", null=True, blank=True
    )
    vendor = models.ForeignKey(Vendor, on_delete=models.PROTECT)
    warehouse = models.ForeignKey(Warehouse, on_delete=models.PROTECT, null=True, blank=True)
    branch = models.ForeignKey(Branch, on_delete=models.PROTECT, null=True, blank=True)
    agent = models.ForeignKey(DeliveryAgent, on_delete=models.PROTECT, null=True, blank=True)

    class Status(models.TextChoices):
        CREATED = "created", "Created"
        AWAITING_PICKUP = "awaiting_pickup", "Awaiting Pickup"
        PICKED_UP = "picked_up", "Picked Up"
        IN_TRANSIT = "in_transit", "In Transit"
        AT_HUB = "at_hub", "At Hub"
        OUT_FOR_DELIVERY = "out_for_delivery", "Out for Delivery"
        DELIVERED = "delivered", "Delivered"
        DELIVERY_FAILED = "delivery_failed", "Delivery Failed"
        RTO_INITIATED = "rto_initiated", "RTO Initiated"
        RTO_IN_TRANSIT = "rto_in_transit", "RTO In Transit"
        RTO_DELIVERED = "rto_delivered", "RTO Delivered"
        CANCELLED = "cancelled", "Cancelled"

    status: models.CharField = models.CharField(max_length=30, choices=Status.choices, default=Status.CREATED)

    VALID_TRANSITIONS = {
        Status.CREATED: {Status.AWAITING_PICKUP, Status.CANCELLED},
        Status.AWAITING_PICKUP: {Status.PICKED_UP, Status.CANCELLED},
        Status.PICKED_UP: {Status.IN_TRANSIT, Status.AT_HUB, Status.CANCELLED},
        Status.IN_TRANSIT: {Status.AT_HUB, Status.OUT_FOR_DELIVERY, Status.CANCELLED},
        Status.AT_HUB: {Status.IN_TRANSIT, Status.OUT_FOR_DELIVERY, Status.CANCELLED},
        Status.OUT_FOR_DELIVERY: {Status.DELIVERED, Status.DELIVERY_FAILED, Status.CANCELLED},
        Status.DELIVERED: set(),  # Final state
        Status.DELIVERY_FAILED: {Status.OUT_FOR_DELIVERY, Status.RTO_INITIATED},  # Retry or RTO
        Status.RTO_INITIATED: {Status.RTO_IN_TRANSIT},
        Status.RTO_IN_TRANSIT: {Status.AT_HUB, Status.RTO_DELIVERED},
        Status.RTO_DELIVERED: set(),  # Final state
        Status.CANCELLED: set(),  # Final state
    }

    def can_transition_to(self, new_status: str) -> bool:
        if self.status == new_status:
            return True
        return new_status in self.VALID_TRANSITIONS.get(self.status, set())

    class Type(models.TextChoices):
        FORWARD = "forward", "Forward"
        REVERSE = "reverse", "Reverse"
        RTO = "rto", "RTO"

    type: models.CharField = models.CharField(max_length=20, choices=Type.choices, default=Type.FORWARD)

    weight = models.DecimalField(max_digits=10, decimal_places=3, null=True, blank=True)
    dimensions = models.JSONField(default=dict, blank=True)
    declared_value = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    is_cod = models.BooleanField(default=False)
    cod_amount = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)

    picked_up_at = models.DateTimeField(null=True, blank=True)
    delivered_at = models.DateTimeField(null=True, blank=True)

    def save(self, *args, **kwargs):
        if self.pk:
            old_instance = Shipment.objects.get(pk=self.pk)
            if old_instance.status != self.status and not self.can_transition_to(self.status):
                raise ValidationError(f"Invalid transition from {old_instance.status} to {self.status}")
        super().save(*args, **kwargs)

    def __str__(self):
        return self.awb

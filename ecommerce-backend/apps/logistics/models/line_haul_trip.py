import hashid_field
from django.core.exceptions import ValidationError
from django.db import models

from common.models import TimestampedMixin

from .hub import Hub


class LineHaulTrip(TimestampedMixin, models.Model):
    id = hashid_field.HashidAutoField(primary_key=True)
    trip_number = models.CharField(max_length=50, unique=True)
    origin_hub = models.ForeignKey(Hub, on_delete=models.CASCADE, related_name="trips_origin")
    dest_hub = models.ForeignKey(Hub, on_delete=models.CASCADE, related_name="trips_dest")
    vehicle_number = models.CharField(max_length=50, blank=True)
    driver_name = models.CharField(max_length=100, blank=True)

    class Status(models.TextChoices):
        SCHEDULED = "scheduled", "Scheduled"
        IN_TRANSIT = "in_transit", "In Transit"
        ARRIVED = "arrived", "Arrived"
        COMPLETED = "completed", "Completed"
        CANCELLED = "cancelled", "Cancelled"

    status: models.CharField = models.CharField(max_length=20, choices=Status.choices, default=Status.SCHEDULED)

    VALID_TRANSITIONS = {
        Status.SCHEDULED: {Status.IN_TRANSIT, Status.CANCELLED},
        Status.IN_TRANSIT: {Status.ARRIVED},
        Status.ARRIVED: {Status.COMPLETED},
        Status.COMPLETED: set(),
        Status.CANCELLED: set(),
    }

    def can_transition_to(self, new_status: str) -> bool:
        if self.status == new_status:
            return True
        return new_status in self.VALID_TRANSITIONS.get(self.status, set())

    package_count = models.PositiveIntegerField(default=0)
    total_weight = models.DecimalField(max_digits=10, decimal_places=3, default=0)

    scheduled_departure = models.DateTimeField(null=True, blank=True)
    actual_departure = models.DateTimeField(null=True, blank=True)
    scheduled_arrival = models.DateTimeField(null=True, blank=True)
    actual_arrival = models.DateTimeField(null=True, blank=True)

    def save(self, *args, **kwargs):
        if self.pk:
            old_instance = LineHaulTrip.objects.get(pk=self.pk)
            if old_instance.status != self.status and not self.can_transition_to(self.status):
                raise ValidationError(f"Invalid transition from {old_instance.status} to {self.status}")
        super().save(*args, **kwargs)

    def __str__(self):
        return self.trip_number

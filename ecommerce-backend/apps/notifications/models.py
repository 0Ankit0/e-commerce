import hashid_field
from django.conf import settings
from django.db import models
from django.utils import timezone

from . import managers


class Notification(models.Model):
    id = hashid_field.HashidAutoField(primary_key=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    type = models.CharField(max_length=64)

    created_at = models.DateTimeField(auto_now_add=True)
    read_at = models.DateTimeField(null=True, blank=True)

    data = models.JSONField(default=dict)

    issuer = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=True, blank=True, related_name="notifications_issued"
    )

    objects = managers.NotificationManager()

    def __str__(self) -> str:
        return str(self.id)

    @property
    def is_read(self) -> bool:
        return self.read_at is not None

    @is_read.setter
    def is_read(self, val: bool):
        self.read_at = timezone.now() if val else None


class ScheduledNotification(models.Model):
    """Model for scheduled notifications to be sent at a future time."""

    id = hashid_field.HashidAutoField(primary_key=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="scheduled_notifications")
    type = models.CharField(max_length=64)
    data = models.JSONField(default=dict)

    scheduled_for = models.DateTimeField()
    sent = models.BooleanField(default=False)
    sent_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["scheduled_for"]
        indexes = [
            models.Index(fields=["scheduled_for", "sent"]),
        ]

    def __str__(self) -> str:
        return f"Scheduled: {self.type} for {self.user} at {self.scheduled_for}"


class NotificationPreference(models.Model):
    """User notification preferences."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="notification_preferences"
    )
    notification_type = models.CharField(max_length=64)

    class Channel(models.TextChoices):
        EMAIL = "email", "Email"
        PUSH = "push", "Push Notification"
        IN_APP = "in_app", "In-App"

    channel = models.CharField(max_length=20, choices=Channel.choices)
    enabled = models.BooleanField(default=True)

    class Meta:
        unique_together = ["user", "notification_type", "channel"]

    def __str__(self) -> str:
        status = "enabled" if self.enabled else "disabled"
        return f"{self.user}: {self.notification_type} via {self.channel} ({status})"

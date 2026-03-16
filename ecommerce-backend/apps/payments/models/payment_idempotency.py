from django.conf import settings
from django.db import models


class PaymentIdempotency(models.Model):
    class Action(models.TextChoices):
        CREATE = "create", "Create"
        VERIFY = "verify", "Verify"

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="payment_idempotency")
    action = models.CharField(max_length=20, choices=Action.choices)
    key = models.CharField(max_length=255)
    response_data = models.JSONField(default=dict)
    status_code = models.PositiveSmallIntegerField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("user", "action", "key")
        indexes = [models.Index(fields=["user", "action", "key"])]

    def __str__(self) -> str:
        return f"{self.user_id}:{self.action}:{self.key}"

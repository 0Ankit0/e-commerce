from django.db import models


class PaymentWebhookEvent(models.Model):
    gateway = models.CharField(max_length=20, default="stripe")
    event_id = models.CharField(max_length=255, unique=True)
    event_type = models.CharField(max_length=255)
    payload = models.JSONField(default=dict)
    payment = models.ForeignKey("payments.Payment", null=True, blank=True, on_delete=models.SET_NULL)
    processed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [models.Index(fields=["gateway", "event_id"])]

    def __str__(self) -> str:
        return f"{self.gateway}:{self.event_id}"

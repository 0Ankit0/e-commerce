from datetime import datetime

from pydantic import BaseModel, field_serializer

from src.apps.iam.utils.hashid import encode_id
from src.apps.notification.models.notification_delivery import (
    NotificationDeliveryChannel,
    NotificationDeliveryStatus,
)


class NotificationDeliveryRead(BaseModel):
    id: int
    notification_id: int
    user_id: int
    channel: NotificationDeliveryChannel
    status: NotificationDeliveryStatus
    provider: str | None
    target: str | None
    attempt_count: int
    max_attempts: int
    last_error_code: str | None
    last_error_reason: str | None
    created_at: datetime
    updated_at: datetime
    last_attempt_at: datetime | None
    next_attempt_at: datetime | None
    delivered_at: datetime | None
    dead_lettered_at: datetime | None

    model_config = {"from_attributes": True}

    @field_serializer("id", "notification_id", "user_id")
    def serialize_ids(self, value: int) -> str:
        return encode_id(value)


class NotificationDeliveryList(BaseModel):
    items: list[NotificationDeliveryRead]
    total: int

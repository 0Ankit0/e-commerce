"""Notification delivery attempt tracking model."""
from datetime import datetime
from enum import Enum
from typing import Optional

from sqlmodel import Field, Relationship, SQLModel

if False:  # pragma: no cover
    from src.apps.notification.models.notification import Notification


class NotificationDeliveryChannel(str, Enum):
    WEBSOCKET = "websocket"
    EMAIL = "email"
    PUSH = "push"
    SMS = "sms"


class NotificationDeliveryStatus(str, Enum):
    QUEUED = "queued"
    SENT = "sent"
    PENDING = "pending"
    RETRYING = "retrying"
    DELIVERED = "delivered"
    FAILED = "failed"
    DEAD_LETTER = "dead_letter"
    SKIPPED = "skipped"


class NotificationDelivery(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    notification_id: int = Field(foreign_key="notification.id", index=True)
    user_id: int = Field(foreign_key="user.id", index=True)

    channel: NotificationDeliveryChannel = Field(index=True)
    status: NotificationDeliveryStatus = Field(default=NotificationDeliveryStatus.PENDING, index=True)
    provider: Optional[str] = Field(default=None, max_length=64)

    target: Optional[str] = Field(default=None, max_length=512)
    dedup_key: str = Field(max_length=255, unique=True, index=True)

    attempt_count: int = Field(default=0)
    retry_count: int = Field(default=0)
    max_attempts: int = Field(default=4)

    last_error_code: Optional[str] = Field(default=None, max_length=128)
    last_error_reason: Optional[str] = Field(default=None, max_length=1024)
    provider_response_code: Optional[str] = Field(default=None, max_length=128)
    provider_response_payload: Optional[str] = Field(default=None, max_length=2048)

    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    queued_at: datetime = Field(default_factory=datetime.now)
    sent_at: Optional[datetime] = Field(default=None)
    last_attempt_at: Optional[datetime] = Field(default=None)
    next_attempt_at: Optional[datetime] = Field(default=None, index=True)
    delivered_at: Optional[datetime] = Field(default=None)
    dead_lettered_at: Optional[datetime] = Field(default=None)

    notification: Optional["Notification"] = Relationship()

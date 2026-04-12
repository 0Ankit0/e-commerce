"""Notification delivery attempt tracking model."""
from datetime import datetime
from enum import Enum
from typing import Any, Optional

from sqlalchemy import JSON, Column
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


class NotificationDeliveryEventType(str, Enum):
    QUEUED = "queued"
    SENT = "sent"
    DELIVERED = "delivered"
    FAILED = "failed"
    RETRY_SCHEDULED = "retry_scheduled"
    DEAD_LETTERED = "dead_lettered"
    OPENED = "opened"
    CLICKED = "clicked"


class NotificationFailureBucket(str, Enum):
    PROVIDER_OUTAGE = "provider_outage"
    RATE_LIMITED = "rate_limited"
    INVALID_RECIPIENT = "invalid_recipient"
    AUTH_CONFIGURATION = "auth_configuration"
    QUOTA_EXCEEDED = "quota_exceeded"
    NETWORK = "network"
    CONTENT_POLICY = "content_policy"
    UNKNOWN = "unknown"


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


class NotificationDeliveryEvent(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    delivery_id: int = Field(foreign_key="notificationdelivery.id", index=True)
    notification_id: int = Field(foreign_key="notification.id", index=True)
    user_id: int = Field(foreign_key="user.id", index=True)

    channel: NotificationDeliveryChannel = Field(index=True)
    event_type: NotificationDeliveryEventType = Field(index=True)
    status_before: NotificationDeliveryStatus | None = Field(default=None)
    status_after: NotificationDeliveryStatus | None = Field(default=None)

    provider: str | None = Field(default=None, max_length=64, index=True)
    provider_response_code: str | None = Field(default=None, max_length=128)
    normalized_error_code: str | None = Field(default=None, max_length=128, index=True)
    failure_bucket: NotificationFailureBucket | None = Field(default=None, index=True)
    error_reason: str | None = Field(default=None, max_length=1024)

    attempt_count: int = Field(default=0)
    latency_ms: int | None = Field(default=None)
    event_metadata_json: dict[str, Any] = Field(default_factory=dict, sa_column=Column("event_metadata", JSON))
    occurred_at: datetime = Field(default_factory=datetime.now, index=True)


class NotificationDeliveryDailySummary(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    day: str = Field(index=True, max_length=10)
    channel: NotificationDeliveryChannel = Field(index=True)
    template: str = Field(index=True, max_length=128)
    provider: str = Field(index=True, max_length=64)
    total_events: int = Field(default=0)
    delivered_events: int = Field(default=0)
    failed_events: int = Field(default=0)
    avg_latency_ms: float = Field(default=0.0)
    p95_latency_ms: float = Field(default=0.0)
    retry_success_count: int = Field(default=0)
    created_at: datetime = Field(default_factory=datetime.now)


class NotificationDeliveryAlert(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    provider: str = Field(index=True, max_length=64)
    channel: NotificationDeliveryChannel = Field(index=True)
    alert_type: str = Field(index=True, max_length=64)
    severity: str = Field(default="warning", max_length=32)
    metric_value: float = Field(default=0.0)
    threshold_value: float = Field(default=0.0)
    message: str = Field(max_length=512)
    observed_window_start: datetime = Field(index=True)
    observed_window_end: datetime = Field(index=True)
    metadata_json: dict[str, Any] = Field(default_factory=dict, sa_column=Column("metadata", JSON))
    created_at: datetime = Field(default_factory=datetime.now, index=True)

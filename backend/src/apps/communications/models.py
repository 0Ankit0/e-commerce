from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Optional

from sqlalchemy import JSON, Column, UniqueConstraint
from sqlmodel import Field, SQLModel

from src.apps.core.time import utc_now


class EmailMessageLifecycleStatus(str, Enum):
    QUEUED = "queued"
    SENT = "sent"
    DELIVERED = "delivered"
    BOUNCED = "bounced"
    COMPLAINED = "complained"
    FAILED = "failed"


class EmailDeliveryMessage(SQLModel, table=True):
    __tablename__ = "email_delivery_messages"  # type: ignore[assignment]

    id: Optional[int] = Field(default=None, primary_key=True)
    subject: str = Field(max_length=255)
    template_name: str = Field(max_length=128)
    status: EmailMessageLifecycleStatus = Field(default=EmailMessageLifecycleStatus.QUEUED, index=True)

    provider: Optional[str] = Field(default=None, max_length=64, index=True)
    provider_message_id: Optional[str] = Field(default=None, max_length=255, index=True)

    recipients_json: list[dict[str, str]] = Field(default_factory=list, sa_column=Column("recipients", JSON))
    context_json: dict[str, Any] = Field(default_factory=dict, sa_column=Column("context", JSON))
    provider_metadata_json: dict[str, Any] = Field(default_factory=dict, sa_column=Column("provider_metadata", JSON))

    attempt_count: int = Field(default=0)
    max_attempts: int = Field(default=4)

    last_error_reason: Optional[str] = Field(default=None, max_length=1024)
    failure_reason: Optional[str] = Field(default=None, max_length=255)

    queued_at: datetime = Field(default_factory=utc_now, index=True)
    sent_at: Optional[datetime] = Field(default=None, index=True)
    delivered_at: Optional[datetime] = Field(default=None, index=True)
    finalized_at: Optional[datetime] = Field(default=None)
    last_attempt_at: Optional[datetime] = Field(default=None)
    next_attempt_at: Optional[datetime] = Field(default=None, index=True)
    dead_lettered_at: Optional[datetime] = Field(default=None, index=True)
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


class EmailDeliveryWebhookEvent(SQLModel, table=True):
    __tablename__ = "email_delivery_webhook_events"  # type: ignore[assignment]
    __table_args__ = (
        UniqueConstraint("provider", "provider_event_id", name="uq_email_webhook_provider_event"),
    )

    id: Optional[int] = Field(default=None, primary_key=True)
    provider: str = Field(max_length=64, index=True)
    provider_event_id: str = Field(max_length=255)
    provider_message_id: str = Field(max_length=255, index=True)
    status: EmailMessageLifecycleStatus = Field(index=True)
    occurred_at: datetime = Field(default_factory=utc_now, index=True)
    received_at: datetime = Field(default_factory=utc_now)
    duplicate: bool = Field(default=False)
    out_of_order: bool = Field(default=False)
    payload_json: dict[str, Any] = Field(default_factory=dict, sa_column=Column("payload", JSON))


class EmailDeliveryDeadLetter(SQLModel, table=True):
    __tablename__ = "email_delivery_dead_letters"  # type: ignore[assignment]

    id: Optional[int] = Field(default=None, primary_key=True)
    message_id: int = Field(foreign_key="email_delivery_messages.id", index=True)
    reason: str = Field(max_length=255)
    payload_json: dict[str, Any] = Field(default_factory=dict, sa_column=Column("payload", JSON))
    created_at: datetime = Field(default_factory=utc_now, index=True)


class QuotaScope(str, Enum):
    GLOBAL = "global"
    TENANT = "tenant"
    USER = "user"
    TENANT_USER = "tenant_user"


class ChannelQuotaPolicy(SQLModel, table=True):
    __tablename__ = "channel_quota_policies"  # type: ignore[assignment]
    __table_args__ = (
        UniqueConstraint(
            "channel",
            "window_seconds",
            "tenant_id",
            "user_id",
            name="uq_channel_quota_policy_scope",
        ),
    )

    id: Optional[int] = Field(default=None, primary_key=True)
    channel: str = Field(default="sms", max_length=32, index=True)
    scope: QuotaScope = Field(default=QuotaScope.GLOBAL, index=True)
    tenant_id: Optional[int] = Field(default=None, foreign_key="tenant.id", index=True)
    user_id: Optional[int] = Field(default=None, foreign_key="user.id", index=True)
    limit_count: int = Field(default=50, ge=1)
    window_seconds: int = Field(default=3600, ge=1)
    timezone: str = Field(default="UTC", max_length=64)
    enabled: bool = Field(default=True, index=True)
    created_at: datetime = Field(default_factory=utc_now, index=True)
    updated_at: datetime = Field(default_factory=utc_now)


class ChannelQuotaUsage(SQLModel, table=True):
    __tablename__ = "channel_quota_usage"  # type: ignore[assignment]
    __table_args__ = (
        UniqueConstraint("policy_id", "window_start", name="uq_channel_quota_usage_bucket"),
    )

    id: Optional[int] = Field(default=None, primary_key=True)
    policy_id: int = Field(foreign_key="channel_quota_policies.id", index=True)
    window_start: datetime = Field(index=True)
    window_end: datetime = Field(index=True)
    usage_count: int = Field(default=0, ge=0)
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


class ChannelQuotaOverrideAudit(SQLModel, table=True):
    __tablename__ = "channel_quota_override_audit"  # type: ignore[assignment]

    id: Optional[int] = Field(default=None, primary_key=True)
    policy_id: int = Field(foreign_key="channel_quota_policies.id", index=True)
    actor_user_id: Optional[int] = Field(default=None, foreign_key="user.id", index=True)
    action: str = Field(max_length=64, index=True)
    reason: str = Field(default="", max_length=512)
    before_json: dict[str, Any] = Field(default_factory=dict, sa_column=Column("before", JSON))
    after_json: dict[str, Any] = Field(default_factory=dict, sa_column=Column("after", JSON))
    metadata_json: dict[str, Any] = Field(default_factory=dict, sa_column=Column("metadata", JSON))
    created_at: datetime = Field(default_factory=utc_now, index=True)

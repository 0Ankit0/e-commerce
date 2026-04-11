from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from sqlalchemy import JSON, Column, UniqueConstraint
from sqlmodel import Field, SQLModel

from src.apps.core.time import utc_now


class SmsQuotaConfig(SQLModel, table=True):
    __tablename__ = "sms_quota_configs"  # type: ignore[assignment]

    id: Optional[int] = Field(default=None, primary_key=True)
    provider: str = Field(default="default", max_length=64, index=True)
    per_user_daily_limit: int | None = Field(default=100, ge=1)
    per_ip_window_limit: int | None = Field(default=25, ge=1)
    ip_window_seconds: int = Field(default=300, ge=1)
    global_provider_daily_limit: int | None = Field(default=10_000, ge=1)
    privileged_override_enabled: bool = Field(default=True)
    updated_by_user_id: int | None = Field(default=None, foreign_key="user.id", index=True)
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now, index=True)


class SmsQuotaCounter(SQLModel, table=True):
    __tablename__ = "sms_quota_counters"  # type: ignore[assignment]
    __table_args__ = (UniqueConstraint("counter_key", name="uq_sms_quota_counter_key"),)

    id: Optional[int] = Field(default=None, primary_key=True)
    counter_key: str = Field(max_length=255, index=True)
    scope: str = Field(max_length=24, index=True)
    provider: str | None = Field(default=None, max_length=64, index=True)
    user_id: int | None = Field(default=None, foreign_key="user.id", index=True)
    ip_address: str | None = Field(default=None, max_length=64, index=True)
    window_start: datetime = Field(index=True)
    window_end: datetime = Field(index=True)
    usage_count: int = Field(default=0, ge=0)
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now, index=True)


class SmsQuotaViolationEvent(SQLModel, table=True):
    __tablename__ = "sms_quota_violation_events"  # type: ignore[assignment]

    id: Optional[int] = Field(default=None, primary_key=True)
    config_id: int | None = Field(default=None, foreign_key="sms_quota_configs.id", index=True)
    scope: str = Field(max_length=24, index=True)
    provider: str | None = Field(default=None, max_length=64, index=True)
    user_id: int | None = Field(default=None, foreign_key="user.id", index=True)
    ip_address: str | None = Field(default=None, max_length=64, index=True)
    limit_count: int = Field(ge=1)
    attempted_count: int = Field(ge=1)
    window_start: datetime
    window_end: datetime
    override_applied: bool = Field(default=False, index=True)
    reason: str = Field(default="quota_exceeded", max_length=255)
    metadata_json: dict[str, Any] = Field(default_factory=dict, sa_column=Column("metadata", JSON))
    created_at: datetime = Field(default_factory=utc_now, index=True)

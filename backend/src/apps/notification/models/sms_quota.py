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
    per_tenant_daily_limit: int | None = Field(default=2_500, ge=1)
    per_phone_window_limit: int | None = Field(default=5, ge=1)
    phone_window_seconds: int = Field(default=600, ge=1)
    per_ip_window_limit: int | None = Field(default=25, ge=1)
    ip_window_seconds: int = Field(default=300, ge=1)
    per_device_window_limit: int | None = Field(default=15, ge=1)
    device_window_seconds: int = Field(default=300, ge=1)
    global_provider_soft_daily_limit: int | None = Field(default=8_000, ge=1)
    global_provider_daily_limit: int | None = Field(default=10_000, ge=1)
    soft_throttle_action: str = Field(default="delay", max_length=24)
    hard_throttle_action: str = Field(default="block", max_length=24)
    soft_throttle_delay_seconds: int = Field(default=30, ge=0)
    hard_throttle_delay_seconds: int = Field(default=0, ge=0)
    hard_cooldown_seconds: int = Field(default=900, ge=0)
    trusted_entry_points_json: dict[str, Any] = Field(default_factory=dict, sa_column=Column("trusted_entry_points", JSON))
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
    tenant_id: int | None = Field(default=None, foreign_key="tenant.id", index=True)
    ip_address: str | None = Field(default=None, max_length=64, index=True)
    phone_number_hash: str | None = Field(default=None, max_length=128, index=True)
    device_fingerprint_hash: str | None = Field(default=None, max_length=128, index=True)
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
    tenant_id: int | None = Field(default=None, foreign_key="tenant.id", index=True)
    ip_address: str | None = Field(default=None, max_length=64, index=True)
    phone_number_hash: str | None = Field(default=None, max_length=128, index=True)
    device_fingerprint_hash: str | None = Field(default=None, max_length=128, index=True)
    limit_count: int = Field(ge=1)
    attempted_count: int = Field(ge=1)
    window_start: datetime
    window_end: datetime
    override_applied: bool = Field(default=False, index=True)
    severity: str = Field(default="hard", max_length=24)
    throttle_action: str = Field(default="block", max_length=24)
    delay_seconds: int = Field(default=0, ge=0)
    cooldown_until: datetime | None = Field(default=None, index=True)
    reason: str = Field(default="quota_exceeded", max_length=255)
    metadata_json: dict[str, Any] = Field(default_factory=dict, sa_column=Column("metadata", JSON))
    created_at: datetime = Field(default_factory=utc_now, index=True)


class SmsQuotaPolicyAuditEvent(SQLModel, table=True):
    __tablename__ = "sms_quota_policy_audit_events"  # type: ignore[assignment]

    id: Optional[int] = Field(default=None, primary_key=True)
    provider: str = Field(default="default", max_length=64, index=True)
    actor_user_id: int | None = Field(default=None, foreign_key="user.id", index=True)
    action: str = Field(default="config_updated", max_length=64)
    changed_fields_json: dict[str, Any] = Field(default_factory=dict, sa_column=Column("changed_fields", JSON))
    impact_summary_json: dict[str, Any] = Field(default_factory=dict, sa_column=Column("impact_summary", JSON))
    created_at: datetime = Field(default_factory=utc_now, index=True)

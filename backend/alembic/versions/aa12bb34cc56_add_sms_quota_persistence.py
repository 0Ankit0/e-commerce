"""add_sms_quota_persistence

Revision ID: aa12bb34cc56
Revises: f4b2c7a9d001
Create Date: 2026-04-11 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel


# revision identifiers, used by Alembic.
revision: str = "aa12bb34cc56"
down_revision: Union[str, Sequence[str], None] = "f4b2c7a9d001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "sms_quota_configs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("provider", sqlmodel.AutoString(length=64), nullable=False),
        sa.Column("per_user_daily_limit", sa.Integer(), nullable=True),
        sa.Column("per_ip_window_limit", sa.Integer(), nullable=True),
        sa.Column("ip_window_seconds", sa.Integer(), nullable=False),
        sa.Column("global_provider_daily_limit", sa.Integer(), nullable=True),
        sa.Column("privileged_override_enabled", sa.Boolean(), nullable=False),
        sa.Column("updated_by_user_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["updated_by_user_id"], ["user.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("sms_quota_configs", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_sms_quota_configs_provider"), ["provider"], unique=False)
        batch_op.create_index(batch_op.f("ix_sms_quota_configs_updated_at"), ["updated_at"], unique=False)
        batch_op.create_index(batch_op.f("ix_sms_quota_configs_updated_by_user_id"), ["updated_by_user_id"], unique=False)

    op.create_table(
        "sms_quota_counters",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("counter_key", sqlmodel.AutoString(length=255), nullable=False),
        sa.Column("scope", sqlmodel.AutoString(length=24), nullable=False),
        sa.Column("provider", sqlmodel.AutoString(length=64), nullable=True),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column("ip_address", sqlmodel.AutoString(length=64), nullable=True),
        sa.Column("window_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("window_end", sa.DateTime(timezone=True), nullable=False),
        sa.Column("usage_count", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["user.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("counter_key", name="uq_sms_quota_counter_key"),
    )
    with op.batch_alter_table("sms_quota_counters", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_sms_quota_counters_counter_key"), ["counter_key"], unique=False)
        batch_op.create_index(batch_op.f("ix_sms_quota_counters_scope"), ["scope"], unique=False)
        batch_op.create_index(batch_op.f("ix_sms_quota_counters_provider"), ["provider"], unique=False)
        batch_op.create_index(batch_op.f("ix_sms_quota_counters_user_id"), ["user_id"], unique=False)
        batch_op.create_index(batch_op.f("ix_sms_quota_counters_ip_address"), ["ip_address"], unique=False)
        batch_op.create_index(batch_op.f("ix_sms_quota_counters_window_start"), ["window_start"], unique=False)
        batch_op.create_index(batch_op.f("ix_sms_quota_counters_window_end"), ["window_end"], unique=False)
        batch_op.create_index(batch_op.f("ix_sms_quota_counters_updated_at"), ["updated_at"], unique=False)

    op.create_table(
        "sms_quota_violation_events",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("config_id", sa.Integer(), nullable=True),
        sa.Column("scope", sqlmodel.AutoString(length=24), nullable=False),
        sa.Column("provider", sqlmodel.AutoString(length=64), nullable=True),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column("ip_address", sqlmodel.AutoString(length=64), nullable=True),
        sa.Column("limit_count", sa.Integer(), nullable=False),
        sa.Column("attempted_count", sa.Integer(), nullable=False),
        sa.Column("window_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("window_end", sa.DateTime(timezone=True), nullable=False),
        sa.Column("override_applied", sa.Boolean(), nullable=False),
        sa.Column("reason", sqlmodel.AutoString(length=255), nullable=False),
        sa.Column("metadata", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["config_id"], ["sms_quota_configs.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["user.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("sms_quota_violation_events", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_sms_quota_violation_events_config_id"), ["config_id"], unique=False)
        batch_op.create_index(batch_op.f("ix_sms_quota_violation_events_scope"), ["scope"], unique=False)
        batch_op.create_index(batch_op.f("ix_sms_quota_violation_events_provider"), ["provider"], unique=False)
        batch_op.create_index(batch_op.f("ix_sms_quota_violation_events_user_id"), ["user_id"], unique=False)
        batch_op.create_index(batch_op.f("ix_sms_quota_violation_events_ip_address"), ["ip_address"], unique=False)
        batch_op.create_index(batch_op.f("ix_sms_quota_violation_events_override_applied"), ["override_applied"], unique=False)
        batch_op.create_index(batch_op.f("ix_sms_quota_violation_events_created_at"), ["created_at"], unique=False)


def downgrade() -> None:
    with op.batch_alter_table("sms_quota_violation_events", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_sms_quota_violation_events_created_at"))
        batch_op.drop_index(batch_op.f("ix_sms_quota_violation_events_override_applied"))
        batch_op.drop_index(batch_op.f("ix_sms_quota_violation_events_ip_address"))
        batch_op.drop_index(batch_op.f("ix_sms_quota_violation_events_user_id"))
        batch_op.drop_index(batch_op.f("ix_sms_quota_violation_events_provider"))
        batch_op.drop_index(batch_op.f("ix_sms_quota_violation_events_scope"))
        batch_op.drop_index(batch_op.f("ix_sms_quota_violation_events_config_id"))
    op.drop_table("sms_quota_violation_events")

    with op.batch_alter_table("sms_quota_counters", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_sms_quota_counters_updated_at"))
        batch_op.drop_index(batch_op.f("ix_sms_quota_counters_window_end"))
        batch_op.drop_index(batch_op.f("ix_sms_quota_counters_window_start"))
        batch_op.drop_index(batch_op.f("ix_sms_quota_counters_ip_address"))
        batch_op.drop_index(batch_op.f("ix_sms_quota_counters_user_id"))
        batch_op.drop_index(batch_op.f("ix_sms_quota_counters_provider"))
        batch_op.drop_index(batch_op.f("ix_sms_quota_counters_scope"))
        batch_op.drop_index(batch_op.f("ix_sms_quota_counters_counter_key"))
    op.drop_table("sms_quota_counters")

    with op.batch_alter_table("sms_quota_configs", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_sms_quota_configs_updated_by_user_id"))
        batch_op.drop_index(batch_op.f("ix_sms_quota_configs_updated_at"))
        batch_op.drop_index(batch_op.f("ix_sms_quota_configs_provider"))
    op.drop_table("sms_quota_configs")

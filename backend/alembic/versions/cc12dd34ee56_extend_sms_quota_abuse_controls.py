"""extend_sms_quota_abuse_controls

Revision ID: cc12dd34ee56
Revises: bb91d8e4c112
Create Date: 2026-04-12 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "cc12dd34ee56"
down_revision: Union[str, Sequence[str], None] = "bb91d8e4c112"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("sms_quota_configs", schema=None) as batch_op:
        batch_op.add_column(sa.Column("per_device_window_limit", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("device_window_seconds", sa.Integer(), nullable=False, server_default="300"))
        batch_op.add_column(sa.Column("hard_cooldown_seconds", sa.Integer(), nullable=False, server_default="900"))
        batch_op.add_column(sa.Column("trusted_entry_points", sa.JSON(), nullable=False, server_default="{}"))

    with op.batch_alter_table("sms_quota_counters", schema=None) as batch_op:
        batch_op.add_column(sa.Column("device_fingerprint_hash", sa.String(length=128), nullable=True))
        batch_op.create_index(batch_op.f("ix_sms_quota_counters_device_fingerprint_hash"), ["device_fingerprint_hash"], unique=False)

    with op.batch_alter_table("sms_quota_violation_events", schema=None) as batch_op:
        batch_op.add_column(sa.Column("device_fingerprint_hash", sa.String(length=128), nullable=True))
        batch_op.add_column(sa.Column("cooldown_until", sa.DateTime(), nullable=True))
        batch_op.create_index(batch_op.f("ix_sms_quota_violation_events_device_fingerprint_hash"), ["device_fingerprint_hash"], unique=False)
        batch_op.create_index(batch_op.f("ix_sms_quota_violation_events_cooldown_until"), ["cooldown_until"], unique=False)

    op.create_table(
        "sms_quota_policy_audit_events",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("provider", sa.String(length=64), nullable=False),
        sa.Column("actor_user_id", sa.Integer(), nullable=True),
        sa.Column("action", sa.String(length=64), nullable=False),
        sa.Column("changed_fields", sa.JSON(), nullable=False),
        sa.Column("impact_summary", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["actor_user_id"], ["user.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_sms_quota_policy_audit_events_provider"), "sms_quota_policy_audit_events", ["provider"], unique=False)
    op.create_index(op.f("ix_sms_quota_policy_audit_events_actor_user_id"), "sms_quota_policy_audit_events", ["actor_user_id"], unique=False)
    op.create_index(op.f("ix_sms_quota_policy_audit_events_created_at"), "sms_quota_policy_audit_events", ["created_at"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_sms_quota_policy_audit_events_created_at"), table_name="sms_quota_policy_audit_events")
    op.drop_index(op.f("ix_sms_quota_policy_audit_events_actor_user_id"), table_name="sms_quota_policy_audit_events")
    op.drop_index(op.f("ix_sms_quota_policy_audit_events_provider"), table_name="sms_quota_policy_audit_events")
    op.drop_table("sms_quota_policy_audit_events")

    with op.batch_alter_table("sms_quota_violation_events", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_sms_quota_violation_events_cooldown_until"))
        batch_op.drop_index(batch_op.f("ix_sms_quota_violation_events_device_fingerprint_hash"))
        batch_op.drop_column("cooldown_until")
        batch_op.drop_column("device_fingerprint_hash")

    with op.batch_alter_table("sms_quota_counters", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_sms_quota_counters_device_fingerprint_hash"))
        batch_op.drop_column("device_fingerprint_hash")

    with op.batch_alter_table("sms_quota_configs", schema=None) as batch_op:
        batch_op.drop_column("trusted_entry_points")
        batch_op.drop_column("hard_cooldown_seconds")
        batch_op.drop_column("device_window_seconds")
        batch_op.drop_column("per_device_window_limit")

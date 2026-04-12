"""expand_sms_quota_policy_engine

Revision ID: bb91d8e4c112
Revises: aa12bb34cc56
Create Date: 2026-04-12 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "bb91d8e4c112"
down_revision: Union[str, Sequence[str], None] = "aa12bb34cc56"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("sms_quota_configs", schema=None) as batch_op:
        batch_op.add_column(sa.Column("per_tenant_daily_limit", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("per_phone_window_limit", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("phone_window_seconds", sa.Integer(), nullable=False, server_default="600"))
        batch_op.add_column(sa.Column("global_provider_soft_daily_limit", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("soft_throttle_action", sa.String(length=24), nullable=False, server_default="delay"))
        batch_op.add_column(sa.Column("hard_throttle_action", sa.String(length=24), nullable=False, server_default="block"))
        batch_op.add_column(sa.Column("soft_throttle_delay_seconds", sa.Integer(), nullable=False, server_default="30"))
        batch_op.add_column(sa.Column("hard_throttle_delay_seconds", sa.Integer(), nullable=False, server_default="0"))

    with op.batch_alter_table("sms_quota_counters", schema=None) as batch_op:
        batch_op.add_column(sa.Column("tenant_id", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("phone_number_hash", sa.String(length=128), nullable=True))
        batch_op.create_foreign_key("fk_sms_quota_counters_tenant_id_tenant", "tenant", ["tenant_id"], ["id"])
        batch_op.create_index(batch_op.f("ix_sms_quota_counters_tenant_id"), ["tenant_id"], unique=False)
        batch_op.create_index(batch_op.f("ix_sms_quota_counters_phone_number_hash"), ["phone_number_hash"], unique=False)

    with op.batch_alter_table("sms_quota_violation_events", schema=None) as batch_op:
        batch_op.add_column(sa.Column("tenant_id", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("phone_number_hash", sa.String(length=128), nullable=True))
        batch_op.add_column(sa.Column("severity", sa.String(length=24), nullable=False, server_default="hard"))
        batch_op.add_column(sa.Column("throttle_action", sa.String(length=24), nullable=False, server_default="block"))
        batch_op.add_column(sa.Column("delay_seconds", sa.Integer(), nullable=False, server_default="0"))
        batch_op.create_foreign_key("fk_sms_quota_violation_events_tenant_id_tenant", "tenant", ["tenant_id"], ["id"])
        batch_op.create_index(batch_op.f("ix_sms_quota_violation_events_tenant_id"), ["tenant_id"], unique=False)
        batch_op.create_index(batch_op.f("ix_sms_quota_violation_events_phone_number_hash"), ["phone_number_hash"], unique=False)


def downgrade() -> None:
    with op.batch_alter_table("sms_quota_violation_events", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_sms_quota_violation_events_phone_number_hash"))
        batch_op.drop_index(batch_op.f("ix_sms_quota_violation_events_tenant_id"))
        batch_op.drop_constraint("fk_sms_quota_violation_events_tenant_id_tenant", type_="foreignkey")
        batch_op.drop_column("delay_seconds")
        batch_op.drop_column("throttle_action")
        batch_op.drop_column("severity")
        batch_op.drop_column("phone_number_hash")
        batch_op.drop_column("tenant_id")

    with op.batch_alter_table("sms_quota_counters", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_sms_quota_counters_phone_number_hash"))
        batch_op.drop_index(batch_op.f("ix_sms_quota_counters_tenant_id"))
        batch_op.drop_constraint("fk_sms_quota_counters_tenant_id_tenant", type_="foreignkey")
        batch_op.drop_column("phone_number_hash")
        batch_op.drop_column("tenant_id")

    with op.batch_alter_table("sms_quota_configs", schema=None) as batch_op:
        batch_op.drop_column("hard_throttle_delay_seconds")
        batch_op.drop_column("soft_throttle_delay_seconds")
        batch_op.drop_column("hard_throttle_action")
        batch_op.drop_column("soft_throttle_action")
        batch_op.drop_column("global_provider_soft_daily_limit")
        batch_op.drop_column("phone_window_seconds")
        batch_op.drop_column("per_phone_window_limit")
        batch_op.drop_column("per_tenant_daily_limit")

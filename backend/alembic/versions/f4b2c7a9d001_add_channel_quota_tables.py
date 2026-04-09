"""add_channel_quota_tables

Revision ID: f4b2c7a9d001
Revises: d1a8b2c4e6f0
Create Date: 2026-04-09 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel


# revision identifiers, used by Alembic.
revision: str = "f4b2c7a9d001"
down_revision: Union[str, Sequence[str], None] = "d1a8b2c4e6f0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "channel_quota_policies",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("channel", sqlmodel.AutoString(length=32), nullable=False),
        sa.Column("scope", sqlmodel.AutoString(length=20), nullable=False),
        sa.Column("tenant_id", sa.Integer(), nullable=True),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column("limit_count", sa.Integer(), nullable=False),
        sa.Column("window_seconds", sa.Integer(), nullable=False),
        sa.Column("timezone", sqlmodel.AutoString(length=64), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenant.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["user.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("channel", "window_seconds", "tenant_id", "user_id", name="uq_channel_quota_policy_scope"),
    )
    with op.batch_alter_table("channel_quota_policies", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_channel_quota_policies_channel"), ["channel"], unique=False)
        batch_op.create_index(batch_op.f("ix_channel_quota_policies_scope"), ["scope"], unique=False)
        batch_op.create_index(batch_op.f("ix_channel_quota_policies_tenant_id"), ["tenant_id"], unique=False)
        batch_op.create_index(batch_op.f("ix_channel_quota_policies_user_id"), ["user_id"], unique=False)
        batch_op.create_index(batch_op.f("ix_channel_quota_policies_enabled"), ["enabled"], unique=False)
        batch_op.create_index(batch_op.f("ix_channel_quota_policies_created_at"), ["created_at"], unique=False)

    op.create_table(
        "channel_quota_usage",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("policy_id", sa.Integer(), nullable=False),
        sa.Column("window_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("window_end", sa.DateTime(timezone=True), nullable=False),
        sa.Column("usage_count", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["policy_id"], ["channel_quota_policies.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("policy_id", "window_start", name="uq_channel_quota_usage_bucket"),
    )
    with op.batch_alter_table("channel_quota_usage", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_channel_quota_usage_policy_id"), ["policy_id"], unique=False)
        batch_op.create_index(batch_op.f("ix_channel_quota_usage_window_start"), ["window_start"], unique=False)
        batch_op.create_index(batch_op.f("ix_channel_quota_usage_window_end"), ["window_end"], unique=False)

    op.create_table(
        "channel_quota_override_audit",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("policy_id", sa.Integer(), nullable=False),
        sa.Column("actor_user_id", sa.Integer(), nullable=True),
        sa.Column("action", sqlmodel.AutoString(length=64), nullable=False),
        sa.Column("reason", sqlmodel.AutoString(length=512), nullable=False),
        sa.Column("before", sa.JSON(), nullable=True),
        sa.Column("after", sa.JSON(), nullable=True),
        sa.Column("metadata", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["actor_user_id"], ["user.id"]),
        sa.ForeignKeyConstraint(["policy_id"], ["channel_quota_policies.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("channel_quota_override_audit", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_channel_quota_override_audit_policy_id"), ["policy_id"], unique=False)
        batch_op.create_index(batch_op.f("ix_channel_quota_override_audit_actor_user_id"), ["actor_user_id"], unique=False)
        batch_op.create_index(batch_op.f("ix_channel_quota_override_audit_action"), ["action"], unique=False)
        batch_op.create_index(batch_op.f("ix_channel_quota_override_audit_created_at"), ["created_at"], unique=False)


def downgrade() -> None:
    with op.batch_alter_table("channel_quota_override_audit", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_channel_quota_override_audit_created_at"))
        batch_op.drop_index(batch_op.f("ix_channel_quota_override_audit_action"))
        batch_op.drop_index(batch_op.f("ix_channel_quota_override_audit_actor_user_id"))
        batch_op.drop_index(batch_op.f("ix_channel_quota_override_audit_policy_id"))
    op.drop_table("channel_quota_override_audit")

    with op.batch_alter_table("channel_quota_usage", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_channel_quota_usage_window_end"))
        batch_op.drop_index(batch_op.f("ix_channel_quota_usage_window_start"))
        batch_op.drop_index(batch_op.f("ix_channel_quota_usage_policy_id"))
    op.drop_table("channel_quota_usage")

    with op.batch_alter_table("channel_quota_policies", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_channel_quota_policies_created_at"))
        batch_op.drop_index(batch_op.f("ix_channel_quota_policies_enabled"))
        batch_op.drop_index(batch_op.f("ix_channel_quota_policies_user_id"))
        batch_op.drop_index(batch_op.f("ix_channel_quota_policies_tenant_id"))
        batch_op.drop_index(batch_op.f("ix_channel_quota_policies_scope"))
        batch_op.drop_index(batch_op.f("ix_channel_quota_policies_channel"))
    op.drop_table("channel_quota_policies")

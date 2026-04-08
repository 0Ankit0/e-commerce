"""Add notification delivery tracking table

Revision ID: c2f9a1d9e6b1
Revises: b7c1d2e3f4a5
Create Date: 2026-04-08 08:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel


# revision identifiers, used by Alembic.
revision: str = "c2f9a1d9e6b1"
down_revision: Union[str, Sequence[str], None] = "b7c1d2e3f4a5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "notificationdelivery",
        sa.Column("notification_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("channel", sqlmodel.AutoString(length=32), nullable=False),
        sa.Column("status", sqlmodel.AutoString(length=32), nullable=False),
        sa.Column("provider", sqlmodel.AutoString(length=64), nullable=True),
        sa.Column("target", sqlmodel.AutoString(length=512), nullable=True),
        sa.Column("dedup_key", sqlmodel.AutoString(length=255), nullable=False),
        sa.Column("attempt_count", sa.Integer(), nullable=False),
        sa.Column("max_attempts", sa.Integer(), nullable=False),
        sa.Column("last_error_code", sqlmodel.AutoString(length=128), nullable=True),
        sa.Column("last_error_reason", sqlmodel.AutoString(length=1024), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("last_attempt_at", sa.DateTime(), nullable=True),
        sa.Column("next_attempt_at", sa.DateTime(), nullable=True),
        sa.Column("delivered_at", sa.DateTime(), nullable=True),
        sa.Column("dead_lettered_at", sa.DateTime(), nullable=True),
        sa.Column("id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["notification_id"], ["notification.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["user.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("dedup_key"),
    )

    with op.batch_alter_table("notificationdelivery", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_notificationdelivery_notification_id"), ["notification_id"], unique=False)
        batch_op.create_index(batch_op.f("ix_notificationdelivery_user_id"), ["user_id"], unique=False)
        batch_op.create_index(batch_op.f("ix_notificationdelivery_channel"), ["channel"], unique=False)
        batch_op.create_index(batch_op.f("ix_notificationdelivery_status"), ["status"], unique=False)
        batch_op.create_index(batch_op.f("ix_notificationdelivery_dedup_key"), ["dedup_key"], unique=True)
        batch_op.create_index(batch_op.f("ix_notificationdelivery_next_attempt_at"), ["next_attempt_at"], unique=False)


def downgrade() -> None:
    with op.batch_alter_table("notificationdelivery", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_notificationdelivery_next_attempt_at"))
        batch_op.drop_index(batch_op.f("ix_notificationdelivery_dedup_key"))
        batch_op.drop_index(batch_op.f("ix_notificationdelivery_status"))
        batch_op.drop_index(batch_op.f("ix_notificationdelivery_channel"))
        batch_op.drop_index(batch_op.f("ix_notificationdelivery_user_id"))
        batch_op.drop_index(batch_op.f("ix_notificationdelivery_notification_id"))

    op.drop_table("notificationdelivery")

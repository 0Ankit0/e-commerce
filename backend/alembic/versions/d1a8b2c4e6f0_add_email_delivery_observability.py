"""Add email delivery observability tables.

Revision ID: d1a8b2c4e6f0
Revises: c2f9a1d9e6b1
Create Date: 2026-04-09 10:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel


revision: str = "d1a8b2c4e6f0"
down_revision: Union[str, Sequence[str], None] = "c2f9a1d9e6b1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "email_delivery_messages",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("subject", sqlmodel.AutoString(length=255), nullable=False),
        sa.Column("template_name", sqlmodel.AutoString(length=128), nullable=False),
        sa.Column("status", sqlmodel.AutoString(length=10), nullable=False),
        sa.Column("provider", sqlmodel.AutoString(length=64), nullable=True),
        sa.Column("provider_message_id", sqlmodel.AutoString(length=255), nullable=True),
        sa.Column("recipients", sa.JSON(), nullable=False),
        sa.Column("context", sa.JSON(), nullable=False),
        sa.Column("provider_metadata", sa.JSON(), nullable=False),
        sa.Column("attempt_count", sa.Integer(), nullable=False),
        sa.Column("max_attempts", sa.Integer(), nullable=False),
        sa.Column("last_error_reason", sqlmodel.AutoString(length=1024), nullable=True),
        sa.Column("failure_reason", sqlmodel.AutoString(length=255), nullable=True),
        sa.Column("queued_at", sa.DateTime(), nullable=False),
        sa.Column("sent_at", sa.DateTime(), nullable=True),
        sa.Column("delivered_at", sa.DateTime(), nullable=True),
        sa.Column("finalized_at", sa.DateTime(), nullable=True),
        sa.Column("last_attempt_at", sa.DateTime(), nullable=True),
        sa.Column("next_attempt_at", sa.DateTime(), nullable=True),
        sa.Column("dead_lettered_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("email_delivery_messages") as batch_op:
        batch_op.create_index(batch_op.f("ix_email_delivery_messages_status"), ["status"], unique=False)
        batch_op.create_index(batch_op.f("ix_email_delivery_messages_provider"), ["provider"], unique=False)
        batch_op.create_index(batch_op.f("ix_email_delivery_messages_provider_message_id"), ["provider_message_id"], unique=False)
        batch_op.create_index(batch_op.f("ix_email_delivery_messages_queued_at"), ["queued_at"], unique=False)
        batch_op.create_index(batch_op.f("ix_email_delivery_messages_sent_at"), ["sent_at"], unique=False)
        batch_op.create_index(batch_op.f("ix_email_delivery_messages_delivered_at"), ["delivered_at"], unique=False)
        batch_op.create_index(batch_op.f("ix_email_delivery_messages_next_attempt_at"), ["next_attempt_at"], unique=False)
        batch_op.create_index(batch_op.f("ix_email_delivery_messages_dead_lettered_at"), ["dead_lettered_at"], unique=False)

    op.create_table(
        "email_delivery_webhook_events",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("provider", sqlmodel.AutoString(length=64), nullable=False),
        sa.Column("provider_event_id", sqlmodel.AutoString(length=255), nullable=False),
        sa.Column("provider_message_id", sqlmodel.AutoString(length=255), nullable=False),
        sa.Column("status", sqlmodel.AutoString(length=10), nullable=False),
        sa.Column("occurred_at", sa.DateTime(), nullable=False),
        sa.Column("received_at", sa.DateTime(), nullable=False),
        sa.Column("duplicate", sa.Boolean(), nullable=False),
        sa.Column("out_of_order", sa.Boolean(), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("provider", "provider_event_id", name="uq_email_webhook_provider_event"),
    )
    with op.batch_alter_table("email_delivery_webhook_events") as batch_op:
        batch_op.create_index(batch_op.f("ix_email_delivery_webhook_events_provider"), ["provider"], unique=False)
        batch_op.create_index(batch_op.f("ix_email_delivery_webhook_events_provider_message_id"), ["provider_message_id"], unique=False)
        batch_op.create_index(batch_op.f("ix_email_delivery_webhook_events_status"), ["status"], unique=False)
        batch_op.create_index(batch_op.f("ix_email_delivery_webhook_events_occurred_at"), ["occurred_at"], unique=False)

    op.create_table(
        "email_delivery_dead_letters",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("message_id", sa.Integer(), nullable=False),
        sa.Column("reason", sqlmodel.AutoString(length=255), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["message_id"], ["email_delivery_messages.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("email_delivery_dead_letters") as batch_op:
        batch_op.create_index(batch_op.f("ix_email_delivery_dead_letters_message_id"), ["message_id"], unique=False)
        batch_op.create_index(batch_op.f("ix_email_delivery_dead_letters_created_at"), ["created_at"], unique=False)


def downgrade() -> None:
    with op.batch_alter_table("email_delivery_dead_letters") as batch_op:
        batch_op.drop_index(batch_op.f("ix_email_delivery_dead_letters_created_at"))
        batch_op.drop_index(batch_op.f("ix_email_delivery_dead_letters_message_id"))
    op.drop_table("email_delivery_dead_letters")

    with op.batch_alter_table("email_delivery_webhook_events") as batch_op:
        batch_op.drop_index(batch_op.f("ix_email_delivery_webhook_events_occurred_at"))
        batch_op.drop_index(batch_op.f("ix_email_delivery_webhook_events_status"))
        batch_op.drop_index(batch_op.f("ix_email_delivery_webhook_events_provider_message_id"))
        batch_op.drop_index(batch_op.f("ix_email_delivery_webhook_events_provider"))
    op.drop_table("email_delivery_webhook_events")

    with op.batch_alter_table("email_delivery_messages") as batch_op:
        batch_op.drop_index(batch_op.f("ix_email_delivery_messages_dead_lettered_at"))
        batch_op.drop_index(batch_op.f("ix_email_delivery_messages_next_attempt_at"))
        batch_op.drop_index(batch_op.f("ix_email_delivery_messages_delivered_at"))
        batch_op.drop_index(batch_op.f("ix_email_delivery_messages_sent_at"))
        batch_op.drop_index(batch_op.f("ix_email_delivery_messages_queued_at"))
        batch_op.drop_index(batch_op.f("ix_email_delivery_messages_provider_message_id"))
        batch_op.drop_index(batch_op.f("ix_email_delivery_messages_provider"))
        batch_op.drop_index(batch_op.f("ix_email_delivery_messages_status"))
    op.drop_table("email_delivery_messages")

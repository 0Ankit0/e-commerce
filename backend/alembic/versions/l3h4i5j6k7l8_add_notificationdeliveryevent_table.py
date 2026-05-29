"""add_notificationdeliveryevent_table

Revision ID: l3h4i5j6k7l8
Revises: k2g3h4i5j6k7
Create Date: 2026-05-29 09:20:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = "l3h4i5j6k7l8"
down_revision: Union[str, Sequence[str], None] = "k2g3h4i5j6k7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    bind = op.get_bind()
    inspector = inspect(bind)

    postgresql.ENUM(
        "QUEUED",
        "SENT",
        "DELIVERED",
        "FAILED",
        "RETRY_SCHEDULED",
        "DEAD_LETTERED",
        "OPENED",
        "CLICKED",
        name="notificationdeliveryeventtype",
    ).create(bind, checkfirst=True)

    postgresql.ENUM(
        "PROVIDER_OUTAGE",
        "RATE_LIMITED",
        "INVALID_RECIPIENT",
        "AUTH_CONFIGURATION",
        "QUOTA_EXCEEDED",
        "NETWORK",
        "CONTENT_POLICY",
        "UNKNOWN",
        name="notificationfailurebucket",
    ).create(bind, checkfirst=True)

    if not inspector.has_table("notificationdeliveryevent"):
        op.create_table(
            "notificationdeliveryevent",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("delivery_id", sa.Integer(), nullable=False),
            sa.Column("notification_id", sa.Integer(), nullable=False),
            sa.Column("user_id", sa.Integer(), nullable=False),
            sa.Column(
                "channel",
                postgresql.ENUM(
                    "WEBSOCKET",
                    "EMAIL",
                    "PUSH",
                    "SMS",
                    name="notificationdeliverychannel",
                    create_type=False,
                ),
                nullable=False,
            ),
            sa.Column(
                "event_type",
                postgresql.ENUM(
                    "QUEUED",
                    "SENT",
                    "DELIVERED",
                    "FAILED",
                    "RETRY_SCHEDULED",
                    "DEAD_LETTERED",
                    "OPENED",
                    "CLICKED",
                    name="notificationdeliveryeventtype",
                    create_type=False,
                ),
                nullable=False,
            ),
            sa.Column(
                "status_before",
                postgresql.ENUM(
                    "QUEUED",
                    "SENT",
                    "PENDING",
                    "RETRYING",
                    "DELIVERED",
                    "FAILED",
                    "DEAD_LETTER",
                    "SKIPPED",
                    name="notificationdeliverystatus",
                    create_type=False,
                ),
                nullable=True,
            ),
            sa.Column(
                "status_after",
                postgresql.ENUM(
                    "QUEUED",
                    "SENT",
                    "PENDING",
                    "RETRYING",
                    "DELIVERED",
                    "FAILED",
                    "DEAD_LETTER",
                    "SKIPPED",
                    name="notificationdeliverystatus",
                    create_type=False,
                ),
                nullable=True,
            ),
            sa.Column("provider", sa.String(length=64), nullable=True),
            sa.Column("provider_response_code", sa.String(length=128), nullable=True),
            sa.Column("normalized_error_code", sa.String(length=128), nullable=True),
            sa.Column(
                "failure_bucket",
                postgresql.ENUM(
                    "PROVIDER_OUTAGE",
                    "RATE_LIMITED",
                    "INVALID_RECIPIENT",
                    "AUTH_CONFIGURATION",
                    "QUOTA_EXCEEDED",
                    "NETWORK",
                    "CONTENT_POLICY",
                    "UNKNOWN",
                    name="notificationfailurebucket",
                    create_type=False,
                ),
                nullable=True,
            ),
            sa.Column("error_reason", sa.String(length=1024), nullable=True),
            sa.Column("attempt_count", sa.Integer(), nullable=False, server_default=sa.text("0")),
            sa.Column("latency_ms", sa.Integer(), nullable=True),
            sa.Column("event_metadata", postgresql.JSON(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::json")),
            sa.Column("occurred_at", sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(["delivery_id"], ["notificationdelivery.id"]),
            sa.ForeignKeyConstraint(["notification_id"], ["notification.id"]),
            sa.ForeignKeyConstraint(["user_id"], ["user.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index("ix_notificationdeliveryevent_delivery_id", "notificationdeliveryevent", ["delivery_id"], unique=False)
        op.create_index("ix_notificationdeliveryevent_notification_id", "notificationdeliveryevent", ["notification_id"], unique=False)
        op.create_index("ix_notificationdeliveryevent_user_id", "notificationdeliveryevent", ["user_id"], unique=False)
        op.create_index("ix_notificationdeliveryevent_channel", "notificationdeliveryevent", ["channel"], unique=False)
        op.create_index("ix_notificationdeliveryevent_event_type", "notificationdeliveryevent", ["event_type"], unique=False)
        op.create_index("ix_notificationdeliveryevent_provider", "notificationdeliveryevent", ["provider"], unique=False)
        op.create_index("ix_notificationdeliveryevent_normalized_error_code", "notificationdeliveryevent", ["normalized_error_code"], unique=False)
        op.create_index("ix_notificationdeliveryevent_failure_bucket", "notificationdeliveryevent", ["failure_bucket"], unique=False)
        op.create_index("ix_notificationdeliveryevent_occurred_at", "notificationdeliveryevent", ["occurred_at"], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    bind = op.get_bind()
    inspector = inspect(bind)

    if inspector.has_table("notificationdeliveryevent"):
        op.drop_index("ix_notificationdeliveryevent_occurred_at", table_name="notificationdeliveryevent")
        op.drop_index("ix_notificationdeliveryevent_failure_bucket", table_name="notificationdeliveryevent")
        op.drop_index("ix_notificationdeliveryevent_normalized_error_code", table_name="notificationdeliveryevent")
        op.drop_index("ix_notificationdeliveryevent_provider", table_name="notificationdeliveryevent")
        op.drop_index("ix_notificationdeliveryevent_event_type", table_name="notificationdeliveryevent")
        op.drop_index("ix_notificationdeliveryevent_channel", table_name="notificationdeliveryevent")
        op.drop_index("ix_notificationdeliveryevent_user_id", table_name="notificationdeliveryevent")
        op.drop_index("ix_notificationdeliveryevent_notification_id", table_name="notificationdeliveryevent")
        op.drop_index("ix_notificationdeliveryevent_delivery_id", table_name="notificationdeliveryevent")
        op.drop_table("notificationdeliveryevent")

    postgresql.ENUM(name="notificationfailurebucket").drop(bind, checkfirst=True)
    postgresql.ENUM(name="notificationdeliveryeventtype").drop(bind, checkfirst=True)

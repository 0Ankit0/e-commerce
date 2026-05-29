"""add_order_events_and_notes_tables

Revision ID: e5f6a7b8c9d0
Revises: d4e5f6a7b8c9
Create Date: 2026-05-29 02:22:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


# revision identifiers, used by Alembic.
revision: str = "e5f6a7b8c9d0"
down_revision: Union[str, Sequence[str], None] = "d4e5f6a7b8c9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    inspector = inspect(op.get_bind())

    if not inspector.has_table("order_events"):
        op.create_table(
            "order_events",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("order_id", sa.Integer(), nullable=False),
            sa.Column("actor_user_id", sa.Integer(), nullable=True),
            sa.Column("event_type", sa.String(length=80), nullable=False),
            sa.Column("message", sa.String(length=500), nullable=False),
            sa.Column("payload_json", sa.Text(), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(["order_id"], ["orders.id"]),
            sa.ForeignKeyConstraint(["actor_user_id"], ["user.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
        with op.batch_alter_table("order_events", schema=None) as batch_op:
            batch_op.create_index("ix_order_events_order_id", ["order_id"], unique=False)
            batch_op.create_index("ix_order_events_actor_user_id", ["actor_user_id"], unique=False)
            batch_op.create_index("ix_order_events_event_type", ["event_type"], unique=False)

    if not inspector.has_table("order_notes"):
        op.create_table(
            "order_notes",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("order_id", sa.Integer(), nullable=False),
            sa.Column("created_by_user_id", sa.Integer(), nullable=True),
            sa.Column("note_type", sa.String(length=50), nullable=False),
            sa.Column("note", sa.String(length=2000), nullable=False),
            sa.Column("is_customer_visible", sa.Boolean(), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(["order_id"], ["orders.id"]),
            sa.ForeignKeyConstraint(["created_by_user_id"], ["user.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
        with op.batch_alter_table("order_notes", schema=None) as batch_op:
            batch_op.create_index("ix_order_notes_order_id", ["order_id"], unique=False)
            batch_op.create_index("ix_order_notes_created_by_user_id", ["created_by_user_id"], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    inspector = inspect(op.get_bind())

    if inspector.has_table("order_notes"):
        with op.batch_alter_table("order_notes", schema=None) as batch_op:
            batch_op.drop_index("ix_order_notes_created_by_user_id")
            batch_op.drop_index("ix_order_notes_order_id")
        op.drop_table("order_notes")

    if inspector.has_table("order_events"):
        with op.batch_alter_table("order_events", schema=None) as batch_op:
            batch_op.drop_index("ix_order_events_event_type")
            batch_op.drop_index("ix_order_events_actor_user_id")
            batch_op.drop_index("ix_order_events_order_id")
        op.drop_table("order_events")
"""add_return_events_table

Revision ID: f6a7b8c9d0e1
Revises: e5f6a7b8c9d0
Create Date: 2026-05-29 02:27:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


# revision identifiers, used by Alembic.
revision: str = "f6a7b8c9d0e1"
down_revision: Union[str, Sequence[str], None] = "e5f6a7b8c9d0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    inspector = inspect(op.get_bind())

    if not inspector.has_table("return_events"):
        op.create_table(
            "return_events",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("return_request_id", sa.Integer(), nullable=False),
            sa.Column("actor_user_id", sa.Integer(), nullable=True),
            sa.Column("event_type", sa.String(length=80), nullable=False),
            sa.Column("message", sa.String(length=500), nullable=False),
            sa.Column("payload_json", sa.Text(), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(["return_request_id"], ["return_requests.id"]),
            sa.ForeignKeyConstraint(["actor_user_id"], ["user.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
        with op.batch_alter_table("return_events", schema=None) as batch_op:
            batch_op.create_index("ix_return_events_return_request_id", ["return_request_id"], unique=False)
            batch_op.create_index("ix_return_events_actor_user_id", ["actor_user_id"], unique=False)
            batch_op.create_index("ix_return_events_event_type", ["event_type"], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    inspector = inspect(op.get_bind())

    if inspector.has_table("return_events"):
        with op.batch_alter_table("return_events", schema=None) as batch_op:
            batch_op.drop_index("ix_return_events_event_type")
            batch_op.drop_index("ix_return_events_actor_user_id")
            batch_op.drop_index("ix_return_events_return_request_id")
        op.drop_table("return_events")
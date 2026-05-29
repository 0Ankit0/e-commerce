"""sync_shipment_tracking_columns

Revision ID: g7b8c9d0e1f2
Revises: f6a7b8c9d0e1
Create Date: 2026-05-29 02:34:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = "g7b8c9d0e1f2"
down_revision: Union[str, Sequence[str], None] = "f6a7b8c9d0e1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    inspector = inspect(op.get_bind())
    if not inspector.has_table("shipment_tracking"):
        return

    columns = {column["name"] for column in inspector.get_columns("shipment_tracking")}
    indexes = {index["name"] for index in inspector.get_indexes("shipment_tracking")}

    with op.batch_alter_table("shipment_tracking", schema=None) as batch_op:
        if "from_status" not in columns:
            batch_op.add_column(
                sa.Column(
                    "from_status",
                    postgresql.ENUM(
                        "PENDING_PAYMENT",
                        "CONFIRMED",
                        "PROCESSING",
                        "PACKED",
                        "SHIPPED",
                        "OUT_FOR_DELIVERY",
                        "DELIVERED",
                        "CANCELLED",
                        "RETURNED",
                        name="orderstatus",
                        create_type=False,
                    ),
                    nullable=True,
                )
            )
        if "actor_type" not in columns:
            batch_op.add_column(sa.Column("actor_type", sa.String(length=40), nullable=False, server_default=sa.text("'system'")))
        if "actor_id" not in columns:
            batch_op.add_column(sa.Column("actor_id", sa.Integer(), nullable=True))
        if "context_json" not in columns:
            batch_op.add_column(sa.Column("context_json", sa.Text(), nullable=False, server_default=sa.text("'{}'")))

    if "actor_id" not in columns and "ix_shipment_tracking_actor_id" not in indexes:
        with op.batch_alter_table("shipment_tracking", schema=None) as batch_op:
            batch_op.create_index("ix_shipment_tracking_actor_id", ["actor_id"], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    inspector = inspect(op.get_bind())
    if not inspector.has_table("shipment_tracking"):
        return

    columns = {column["name"] for column in inspector.get_columns("shipment_tracking")}
    indexes = {index["name"] for index in inspector.get_indexes("shipment_tracking")}

    with op.batch_alter_table("shipment_tracking", schema=None) as batch_op:
        if "ix_shipment_tracking_actor_id" in indexes:
            batch_op.drop_index("ix_shipment_tracking_actor_id")
        if "context_json" in columns:
            batch_op.drop_column("context_json")
        if "actor_id" in columns:
            batch_op.drop_column("actor_id")
        if "actor_type" in columns:
            batch_op.drop_column("actor_type")
        if "from_status" in columns:
            batch_op.drop_column("from_status")
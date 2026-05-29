"""add_reverse_pickup_received_at

Revision ID: h8c9d0e1f2g3
Revises: g7b8c9d0e1f2
Create Date: 2026-05-29 08:30:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


# revision identifiers, used by Alembic.
revision: str = "h8c9d0e1f2g3"
down_revision: Union[str, Sequence[str], None] = "g7b8c9d0e1f2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    inspector = inspect(op.get_bind())
    if not inspector.has_table("reverse_pickup_jobs"):
        return

    columns = {column["name"] for column in inspector.get_columns("reverse_pickup_jobs")}
    if "received_at" in columns:
        return

    with op.batch_alter_table("reverse_pickup_jobs", schema=None) as batch_op:
        batch_op.add_column(sa.Column("received_at", sa.DateTime(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    inspector = inspect(op.get_bind())
    if not inspector.has_table("reverse_pickup_jobs"):
        return

    columns = {column["name"] for column in inspector.get_columns("reverse_pickup_jobs")}
    if "received_at" not in columns:
        return

    with op.batch_alter_table("reverse_pickup_jobs", schema=None) as batch_op:
        batch_op.drop_column("received_at")

"""add_notificationdelivery_retry_count

Revision ID: i0e1f2g3h4i5
Revises: h9d0e1f2g3h4
Create Date: 2026-05-29 09:08:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


# revision identifiers, used by Alembic.
revision: str = "i0e1f2g3h4i5"
down_revision: Union[str, Sequence[str], None] = "h9d0e1f2g3h4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    inspector = inspect(op.get_bind())
    if not inspector.has_table("notificationdelivery"):
        return

    columns = {column["name"] for column in inspector.get_columns("notificationdelivery")}
    if "retry_count" in columns:
        return

    with op.batch_alter_table("notificationdelivery", schema=None) as batch_op:
        batch_op.add_column(sa.Column("retry_count", sa.Integer(), nullable=False, server_default=sa.text("0")))


def downgrade() -> None:
    """Downgrade schema."""
    inspector = inspect(op.get_bind())
    if not inspector.has_table("notificationdelivery"):
        return

    columns = {column["name"] for column in inspector.get_columns("notificationdelivery")}
    if "retry_count" not in columns:
        return

    with op.batch_alter_table("notificationdelivery", schema=None) as batch_op:
        batch_op.drop_column("retry_count")

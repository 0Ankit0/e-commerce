"""sync_notificationdelivery_columns

Revision ID: j1f2g3h4i5j6
Revises: i0e1f2g3h4i5
Create Date: 2026-05-29 09:12:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


# revision identifiers, used by Alembic.
revision: str = "j1f2g3h4i5j6"
down_revision: Union[str, Sequence[str], None] = "i0e1f2g3h4i5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    inspector = inspect(op.get_bind())
    if not inspector.has_table("notificationdelivery"):
        return

    columns = {column["name"] for column in inspector.get_columns("notificationdelivery")}

    with op.batch_alter_table("notificationdelivery", schema=None) as batch_op:
        if "provider_response_code" not in columns:
            batch_op.add_column(sa.Column("provider_response_code", sa.String(length=128), nullable=True))
        if "provider_response_payload" not in columns:
            batch_op.add_column(sa.Column("provider_response_payload", sa.String(length=2048), nullable=True))
        if "queued_at" not in columns:
            batch_op.add_column(
                sa.Column(
                    "queued_at",
                    sa.DateTime(),
                    nullable=False,
                    server_default=sa.text("CURRENT_TIMESTAMP"),
                )
            )
        if "sent_at" not in columns:
            batch_op.add_column(sa.Column("sent_at", sa.DateTime(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    inspector = inspect(op.get_bind())
    if not inspector.has_table("notificationdelivery"):
        return

    columns = {column["name"] for column in inspector.get_columns("notificationdelivery")}

    with op.batch_alter_table("notificationdelivery", schema=None) as batch_op:
        if "sent_at" in columns:
            batch_op.drop_column("sent_at")
        if "queued_at" in columns:
            batch_op.drop_column("queued_at")
        if "provider_response_payload" in columns:
            batch_op.drop_column("provider_response_payload")
        if "provider_response_code" in columns:
            batch_op.drop_column("provider_response_code")

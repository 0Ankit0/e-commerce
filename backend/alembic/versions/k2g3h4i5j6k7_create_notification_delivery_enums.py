"""create_notification_delivery_enums

Revision ID: k2g3h4i5j6k7
Revises: j1f2g3h4i5j6
Create Date: 2026-05-29 09:16:00.000000

"""

from typing import Sequence, Union

from alembic import op
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = "k2g3h4i5j6k7"
down_revision: Union[str, Sequence[str], None] = "j1f2g3h4i5j6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    bind = op.get_bind()

    postgresql.ENUM(
        "WEBSOCKET",
        "EMAIL",
        "PUSH",
        "SMS",
        name="notificationdeliverychannel",
    ).create(bind, checkfirst=True)

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
    ).create(bind, checkfirst=True)


def downgrade() -> None:
    """Downgrade schema."""
    bind = op.get_bind()
    postgresql.ENUM(name="notificationdeliverystatus").drop(bind, checkfirst=True)
    postgresql.ENUM(name="notificationdeliverychannel").drop(bind, checkfirst=True)

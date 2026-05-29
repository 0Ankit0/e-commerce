"""add_category_updated_at

Revision ID: f1c2e3d4b5a6
Revises: d4f1a2b3c4d5
Create Date: 2026-05-21 14:50:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "f1c2e3d4b5a6"
down_revision: Union[str, Sequence[str], None] = "d4f1a2b3c4d5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    with op.batch_alter_table("categories", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                "updated_at",
                sa.DateTime(),
                nullable=False,
                server_default=sa.text("CURRENT_TIMESTAMP"),
            )
        )

    with op.batch_alter_table("categories", schema=None) as batch_op:
        batch_op.alter_column("updated_at", server_default=None)


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table("categories", schema=None) as batch_op:
        batch_op.drop_column("updated_at")
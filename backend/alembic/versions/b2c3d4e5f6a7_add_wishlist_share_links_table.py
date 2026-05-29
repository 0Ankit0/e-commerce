"""add_wishlist_share_links_table

Revision ID: b2c3d4e5f6a7
Revises: a7b8c9d0e1f2
Create Date: 2026-05-21 15:20:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel


# revision identifiers, used by Alembic.
revision: str = "b2c3d4e5f6a7"
down_revision: Union[str, Sequence[str], None] = "a7b8c9d0e1f2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "wishlist_share_links",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("token", sqlmodel.AutoString(length=80), nullable=False),
        sa.Column("title", sqlmodel.AutoString(length=255), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["user.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("wishlist_share_links", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_wishlist_share_links_token"), ["token"], unique=True)
        batch_op.create_index(batch_op.f("ix_wishlist_share_links_user_id"), ["user_id"], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table("wishlist_share_links", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_wishlist_share_links_user_id"))
        batch_op.drop_index(batch_op.f("ix_wishlist_share_links_token"))

    op.drop_table("wishlist_share_links")
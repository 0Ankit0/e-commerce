"""add_product_search_documents

Revision ID: d4f1a2b3c4d5
Revises: cc12dd34ee56, 7f3c17e67b4a
Create Date: 2026-04-27 18:55:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel


# revision identifiers, used by Alembic.
revision: str = "d4f1a2b3c4d5"
down_revision: Union[str, Sequence[str], None] = ("cc12dd34ee56", "7f3c17e67b4a")
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "product_search_documents",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("product_id", sa.Integer(), nullable=False),
        sa.Column("title_text", sqlmodel.AutoString(), nullable=False),
        sa.Column("summary_text", sqlmodel.AutoString(), nullable=False),
        sa.Column("body_text", sqlmodel.AutoString(), nullable=False),
        sa.Column("facet_text", sqlmodel.AutoString(), nullable=False),
        sa.Column("keyword_text", sqlmodel.AutoString(), nullable=False),
        sa.Column("searchable_text", sqlmodel.AutoString(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("product_search_documents", schema=None) as batch_op:
        batch_op.create_index(
            batch_op.f("ix_product_search_documents_product_id"),
            ["product_id"],
            unique=True,
        )


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table("product_search_documents", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_product_search_documents_product_id"))
    op.drop_table("product_search_documents")

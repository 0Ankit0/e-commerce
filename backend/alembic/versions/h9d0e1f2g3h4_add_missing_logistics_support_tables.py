"""add_missing_logistics_support_tables

Revision ID: h9d0e1f2g3h4
Revises: h8c9d0e1f2g3
Create Date: 2026-05-29 08:35:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = "h9d0e1f2g3h4"
down_revision: Union[str, Sequence[str], None] = "h8c9d0e1f2g3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    bind = op.get_bind()
    inspector = inspect(bind)

    delivery_exception_status = postgresql.ENUM(
        "open",
        "rescheduled",
        "rto_initiated",
        "resolved",
        name="deliveryexceptionstatus",
    )
    delivery_exception_status.create(bind, checkfirst=True)

    tables = set(inspector.get_table_names())

    if "delivery_exceptions" not in tables:
        op.create_table(
            "delivery_exceptions",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("shipment_id", sa.Integer(), nullable=False),
            sa.Column("agent_id", sa.Integer(), nullable=True),
            sa.Column("exception_type", sa.String(length=80), nullable=False),
            sa.Column("failure_reason", sa.String(length=255), nullable=False, server_default=sa.text("''")),
            sa.Column("notes", sa.String(length=500), nullable=False, server_default=sa.text("''")),
            sa.Column("rescheduled_for", sa.DateTime(), nullable=True),
            sa.Column("rto_initiated_at", sa.DateTime(), nullable=True),
            sa.Column(
                "status",
                postgresql.ENUM(
                    "open",
                    "rescheduled",
                    "rto_initiated",
                    "resolved",
                    name="deliveryexceptionstatus",
                    create_type=False,
                ),
                nullable=False,
                server_default=sa.text("'open'"),
            ),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(["agent_id"], ["delivery_agents.id"]),
            sa.ForeignKeyConstraint(["shipment_id"], ["shipments.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index("ix_delivery_exceptions_shipment_id", "delivery_exceptions", ["shipment_id"], unique=False)
        op.create_index("ix_delivery_exceptions_agent_id", "delivery_exceptions", ["agent_id"], unique=False)
        op.create_index("ix_delivery_exceptions_exception_type", "delivery_exceptions", ["exception_type"], unique=False)

    if "branch_inventory_movements" not in tables:
        op.create_table(
            "branch_inventory_movements",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("branch_id", sa.Integer(), nullable=False),
            sa.Column("shipment_id", sa.Integer(), nullable=True),
            sa.Column("variant_id", sa.Integer(), nullable=True),
            sa.Column("movement_type", sa.String(length=40), nullable=False),
            sa.Column("quantity", sa.Integer(), nullable=False, server_default=sa.text("0")),
            sa.Column("notes", sa.String(length=255), nullable=False, server_default=sa.text("''")),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(["branch_id"], ["logistics_branches.id"]),
            sa.ForeignKeyConstraint(["shipment_id"], ["shipments.id"]),
            sa.ForeignKeyConstraint(["variant_id"], ["product_variants.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index("ix_branch_inventory_movements_branch_id", "branch_inventory_movements", ["branch_id"], unique=False)
        op.create_index("ix_branch_inventory_movements_shipment_id", "branch_inventory_movements", ["shipment_id"], unique=False)
        op.create_index("ix_branch_inventory_movements_variant_id", "branch_inventory_movements", ["variant_id"], unique=False)
        op.create_index("ix_branch_inventory_movements_movement_type", "branch_inventory_movements", ["movement_type"], unique=False)

    if "route_optimization_plans" not in tables:
        op.create_table(
            "route_optimization_plans",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("manifest_id", sa.Integer(), nullable=True),
            sa.Column("trip_id", sa.Integer(), nullable=True),
            sa.Column("strategy", sa.String(length=80), nullable=False, server_default=sa.text("'nearest_neighbor_2opt_v1'")),
            sa.Column("total_distance_km", sa.Float(), nullable=False, server_default=sa.text("0")),
            sa.Column("estimated_duration_minutes", sa.Integer(), nullable=False, server_default=sa.text("0")),
            sa.Column("routed_stop_count", sa.Integer(), nullable=False, server_default=sa.text("0")),
            sa.Column("unroutable_stop_count", sa.Integer(), nullable=False, server_default=sa.text("0")),
            sa.Column("score", sa.Float(), nullable=False, server_default=sa.text("0")),
            sa.Column("stops_json", sa.Text(), nullable=False, server_default=sa.text("'[]'")),
            sa.Column("metrics_json", sa.Text(), nullable=False, server_default=sa.text("'{}'")),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(["manifest_id"], ["shipment_manifests.id"]),
            sa.ForeignKeyConstraint(["trip_id"], ["line_haul_trips.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index("ix_route_optimization_plans_manifest_id", "route_optimization_plans", ["manifest_id"], unique=False)
        op.create_index("ix_route_optimization_plans_trip_id", "route_optimization_plans", ["trip_id"], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    bind = op.get_bind()
    inspector = inspect(bind)
    tables = set(inspector.get_table_names())

    if "route_optimization_plans" in tables:
        op.drop_index("ix_route_optimization_plans_trip_id", table_name="route_optimization_plans")
        op.drop_index("ix_route_optimization_plans_manifest_id", table_name="route_optimization_plans")
        op.drop_table("route_optimization_plans")

    if "branch_inventory_movements" in tables:
        op.drop_index("ix_branch_inventory_movements_movement_type", table_name="branch_inventory_movements")
        op.drop_index("ix_branch_inventory_movements_variant_id", table_name="branch_inventory_movements")
        op.drop_index("ix_branch_inventory_movements_shipment_id", table_name="branch_inventory_movements")
        op.drop_index("ix_branch_inventory_movements_branch_id", table_name="branch_inventory_movements")
        op.drop_table("branch_inventory_movements")

    if "delivery_exceptions" in tables:
        op.drop_index("ix_delivery_exceptions_exception_type", table_name="delivery_exceptions")
        op.drop_index("ix_delivery_exceptions_agent_id", table_name="delivery_exceptions")
        op.drop_index("ix_delivery_exceptions_shipment_id", table_name="delivery_exceptions")
        op.drop_table("delivery_exceptions")

    postgresql.ENUM(name="deliveryexceptionstatus").drop(bind, checkfirst=True)

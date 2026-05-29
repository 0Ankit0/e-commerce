"""sync_vendor_onboarding_schema

Revision ID: c3d4e5f6a7b8
Revises: b2c3d4e5f6a7
Create Date: 2026-05-21 16:25:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = "c3d4e5f6a7b8"
down_revision: Union[str, Sequence[str], None] = "b2c3d4e5f6a7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _rename_enum_value(enum_name: str, old_value: str, new_value: str) -> None:
    op.execute(
        f"""
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1
                FROM pg_type t
                JOIN pg_enum e ON t.oid = e.enumtypid
                WHERE t.typname = '{enum_name}' AND e.enumlabel = '{old_value}'
            ) AND NOT EXISTS (
                SELECT 1
                FROM pg_type t
                JOIN pg_enum e ON t.oid = e.enumtypid
                WHERE t.typname = '{enum_name}' AND e.enumlabel = '{new_value}'
            ) THEN
                ALTER TYPE {enum_name} RENAME VALUE '{old_value}' TO '{new_value}';
            END IF;
        END
        $$;
        """
    )


def _add_enum_value(enum_name: str, value: str) -> None:
    op.execute(
        f"""
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1 FROM pg_type WHERE typname = '{enum_name}'
            ) AND NOT EXISTS (
                SELECT 1
                FROM pg_type t
                JOIN pg_enum e ON t.oid = e.enumtypid
                WHERE t.typname = '{enum_name}' AND e.enumlabel = '{value}'
            ) THEN
                ALTER TYPE {enum_name} ADD VALUE '{value}';
            END IF;
        END
        $$;
        """
    )


def _create_enum_type(enum_name: str, values: list[str]) -> None:
    values_sql = ", ".join(f"'{value}'" for value in values)
    op.execute(
        f"""
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_type WHERE typname = '{enum_name}'
            ) THEN
                CREATE TYPE {enum_name} AS ENUM ({values_sql});
            END IF;
        END
        $$;
        """
    )


def _table_columns(table_name: str) -> set[str]:
    inspector = inspect(op.get_bind())
    if not inspector.has_table(table_name):
        return set()
    return {column["name"] for column in inspector.get_columns(table_name)}


def _table_indexes(table_name: str) -> set[str]:
    inspector = inspect(op.get_bind())
    if not inspector.has_table(table_name):
        return set()
    return {index["name"] for index in inspector.get_indexes(table_name)}


def upgrade() -> None:
    """Upgrade schema."""
    _rename_enum_value("vendorstatus", "PENDING", "pending")
    _rename_enum_value("vendorstatus", "APPROVED", "approved")
    _rename_enum_value("vendorstatus", "REJECTED", "rejected")
    _rename_enum_value("vendorstatus", "SUSPENDED", "suspended")
    _add_enum_value("vendorstatus", "needs_resubmission")
    _add_enum_value("vendorstatus", "under_review")

    _rename_enum_value("commissiontier", "STANDARD", "standard")
    _rename_enum_value("commissiontier", "PREMIUM", "premium")
    _rename_enum_value("commissiontier", "ENTERPRISE", "enterprise")

    _rename_enum_value("bankaccountverificationstatus", "PENDING", "pending")
    _rename_enum_value("bankaccountverificationstatus", "VERIFIED", "verified")
    _rename_enum_value("bankaccountverificationstatus", "FAILED", "failed")

    _rename_enum_value("vendordocumentstatus", "PENDING", "submitted")
    _rename_enum_value("vendordocumentstatus", "VERIFIED", "verified")
    _rename_enum_value("vendordocumentstatus", "REJECTED", "rejected")
    _add_enum_value("vendordocumentstatus", "under_review")
    _add_enum_value("vendordocumentstatus", "needs_resubmission")

    _rename_enum_value("vendorpayoutstatus", "PENDING", "pending")
    _rename_enum_value("vendorpayoutstatus", "PROCESSING", "processing")
    _rename_enum_value("vendorpayoutstatus", "PAID", "paid")
    _rename_enum_value("vendorpayoutstatus", "FAILED", "failed")
    _add_enum_value("vendorpayoutstatus", "requested")

    _create_enum_type(
        "vendorkycstatus",
        [
            "submitted",
            "under_review",
            "resubmission_required",
            "approved",
            "rejected",
            "suspended_after_approval",
        ],
    )

    vendor_columns = _table_columns("vendors")
    if vendor_columns:
        with op.batch_alter_table("vendors", schema=None) as batch_op:
            if "onboarding_step" not in vendor_columns:
                batch_op.add_column(sa.Column("onboarding_step", sa.String(length=80), nullable=False, server_default=sa.text("'profile_submitted'")))
            if "kyc_status" not in vendor_columns:
                batch_op.add_column(
                    sa.Column(
                        "kyc_status",
                        postgresql.ENUM(
                            "submitted",
                            "under_review",
                            "resubmission_required",
                            "approved",
                            "rejected",
                            "suspended_after_approval",
                            name="vendorkycstatus",
                            create_type=False,
                        ),
                        nullable=False,
                        server_default=sa.text("'submitted'"),
                    )
                )
            if "kyc_submitted_at" not in vendor_columns:
                batch_op.add_column(sa.Column("kyc_submitted_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")))
            if "kyc_review_started_at" not in vendor_columns:
                batch_op.add_column(sa.Column("kyc_review_started_at", sa.DateTime(), nullable=True))
            if "kyc_reviewed_at" not in vendor_columns:
                batch_op.add_column(sa.Column("kyc_reviewed_at", sa.DateTime(), nullable=True))
            if "kyc_last_reviewer_user_id" not in vendor_columns:
                batch_op.add_column(sa.Column("kyc_last_reviewer_user_id", sa.Integer(), nullable=True))
            if "kyc_assigned_reviewer_user_id" not in vendor_columns:
                batch_op.add_column(sa.Column("kyc_assigned_reviewer_user_id", sa.Integer(), nullable=True))
            if "kyc_reviewer_assigned_at" not in vendor_columns:
                batch_op.add_column(sa.Column("kyc_reviewer_assigned_at", sa.DateTime(), nullable=True))
            if "kyc_review_reasons_json" not in vendor_columns:
                batch_op.add_column(sa.Column("kyc_review_reasons_json", sa.Text(), nullable=False, server_default=sa.text("'[]'")))
            if "verification_timeline_json" not in vendor_columns:
                batch_op.add_column(sa.Column("verification_timeline_json", sa.Text(), nullable=False, server_default=sa.text("'[]'")))

        vendor_indexes = _table_indexes("vendors")
        with op.batch_alter_table("vendors", schema=None) as batch_op:
            if "ix_vendors_kyc_status" not in vendor_indexes:
                batch_op.create_index("ix_vendors_kyc_status", ["kyc_status"], unique=False)
            if "ix_vendors_kyc_last_reviewer_user_id" not in vendor_indexes:
                batch_op.create_index("ix_vendors_kyc_last_reviewer_user_id", ["kyc_last_reviewer_user_id"], unique=False)
            if "ix_vendors_kyc_assigned_reviewer_user_id" not in vendor_indexes:
                batch_op.create_index("ix_vendors_kyc_assigned_reviewer_user_id", ["kyc_assigned_reviewer_user_id"], unique=False)

    bank_account_columns = _table_columns("vendor_bank_accounts")
    if bank_account_columns and "remarks" not in bank_account_columns:
        with op.batch_alter_table("vendor_bank_accounts", schema=None) as batch_op:
            batch_op.add_column(sa.Column("remarks", sa.String(length=500), nullable=False, server_default=sa.text("''")))

    vendor_document_columns = _table_columns("vendor_documents")
    if vendor_document_columns:
        with op.batch_alter_table("vendor_documents", schema=None) as batch_op:
            if "version" not in vendor_document_columns:
                batch_op.add_column(sa.Column("version", sa.Integer(), nullable=False, server_default=sa.text("1")))
            if "is_current" not in vendor_document_columns:
                batch_op.add_column(sa.Column("is_current", sa.Boolean(), nullable=False, server_default=sa.text("true")))
            if "reviewed_by_user_id" not in vendor_document_columns:
                batch_op.add_column(sa.Column("reviewed_by_user_id", sa.Integer(), nullable=True))
            if "resubmission_requested_at" not in vendor_document_columns:
                batch_op.add_column(sa.Column("resubmission_requested_at", sa.DateTime(), nullable=True))
            if "review_reason_history_json" not in vendor_document_columns:
                batch_op.add_column(sa.Column("review_reason_history_json", sa.Text(), nullable=False, server_default=sa.text("'[]'")))

        vendor_document_indexes = _table_indexes("vendor_documents")
        with op.batch_alter_table("vendor_documents", schema=None) as batch_op:
            if "ix_vendor_documents_is_current" not in vendor_document_indexes:
                batch_op.create_index("ix_vendor_documents_is_current", ["is_current"], unique=False)
            if "ix_vendor_documents_reviewed_by_user_id" not in vendor_document_indexes:
                batch_op.create_index("ix_vendor_documents_reviewed_by_user_id", ["reviewed_by_user_id"], unique=False)

    if not inspect(op.get_bind()).has_table("vendor_payout_batches"):
        op.create_table(
            "vendor_payout_batches",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("code", sa.String(length=80), nullable=False),
            sa.Column(
                "status",
                postgresql.ENUM(
                    "requested",
                    "pending",
                    "processing",
                    "paid",
                    "failed",
                    name="vendorpayoutstatus",
                    create_type=False,
                ),
                nullable=False,
            ),
            sa.Column("total_amount", sa.Float(), nullable=False),
            sa.Column("item_count", sa.Integer(), nullable=False),
            sa.Column("settlement_export_url", sa.String(length=500), nullable=False),
            sa.Column("notes", sa.String(length=500), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("processed_at", sa.DateTime(), nullable=True),
            sa.PrimaryKeyConstraint("id"),
        )
        with op.batch_alter_table("vendor_payout_batches", schema=None) as batch_op:
            batch_op.create_index("ix_vendor_payout_batches_code", ["code"], unique=True)

    vendor_payout_columns = _table_columns("vendor_payouts")
    if vendor_payout_columns and "payout_batch_id" not in vendor_payout_columns:
        with op.batch_alter_table("vendor_payouts", schema=None) as batch_op:
            batch_op.add_column(sa.Column("payout_batch_id", sa.Integer(), nullable=True))
        vendor_payout_indexes = _table_indexes("vendor_payouts")
        with op.batch_alter_table("vendor_payouts", schema=None) as batch_op:
            if "ix_vendor_payouts_payout_batch_id" not in vendor_payout_indexes:
                batch_op.create_index("ix_vendor_payouts_payout_batch_id", ["payout_batch_id"], unique=False)

    if not inspect(op.get_bind()).has_table("vendor_timeline_events"):
        op.create_table(
            "vendor_timeline_events",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("vendor_id", sa.Integer(), nullable=False),
            sa.Column("actor_user_id", sa.Integer(), nullable=True),
            sa.Column("event_type", sa.String(length=80), nullable=False),
            sa.Column("message", sa.String(length=500), nullable=False),
            sa.Column("payload_json", sa.Text(), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(["vendor_id"], ["vendors.id"]),
            sa.ForeignKeyConstraint(["actor_user_id"], ["user.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
        with op.batch_alter_table("vendor_timeline_events", schema=None) as batch_op:
            batch_op.create_index("ix_vendor_timeline_events_vendor_id", ["vendor_id"], unique=False)
            batch_op.create_index("ix_vendor_timeline_events_actor_user_id", ["actor_user_id"], unique=False)
            batch_op.create_index("ix_vendor_timeline_events_event_type", ["event_type"], unique=False)

    if not inspect(op.get_bind()).has_table("vendor_payout_requests"):
        op.create_table(
            "vendor_payout_requests",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("vendor_id", sa.Integer(), nullable=False),
            sa.Column("requested_by_user_id", sa.Integer(), nullable=False),
            sa.Column("amount", sa.Float(), nullable=False),
            sa.Column("currency", sa.String(length=3), nullable=False),
            sa.Column("notes", sa.String(length=500), nullable=False),
            sa.Column(
                "status",
                postgresql.ENUM(
                    "requested",
                    "pending",
                    "processing",
                    "paid",
                    "failed",
                    name="vendorpayoutstatus",
                    create_type=False,
                ),
                nullable=False,
            ),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("reviewed_at", sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(["vendor_id"], ["vendors.id"]),
            sa.ForeignKeyConstraint(["requested_by_user_id"], ["user.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
        with op.batch_alter_table("vendor_payout_requests", schema=None) as batch_op:
            batch_op.create_index("ix_vendor_payout_requests_vendor_id", ["vendor_id"], unique=False)
            batch_op.create_index("ix_vendor_payout_requests_requested_by_user_id", ["requested_by_user_id"], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    inspector = inspect(op.get_bind())

    if inspector.has_table("vendor_payout_requests"):
        with op.batch_alter_table("vendor_payout_requests", schema=None) as batch_op:
            batch_op.drop_index("ix_vendor_payout_requests_requested_by_user_id")
            batch_op.drop_index("ix_vendor_payout_requests_vendor_id")
        op.drop_table("vendor_payout_requests")

    if inspector.has_table("vendor_timeline_events"):
        with op.batch_alter_table("vendor_timeline_events", schema=None) as batch_op:
            batch_op.drop_index("ix_vendor_timeline_events_event_type")
            batch_op.drop_index("ix_vendor_timeline_events_actor_user_id")
            batch_op.drop_index("ix_vendor_timeline_events_vendor_id")
        op.drop_table("vendor_timeline_events")

    if inspector.has_table("vendor_payout_batches"):
        with op.batch_alter_table("vendor_payout_batches", schema=None) as batch_op:
            batch_op.drop_index("ix_vendor_payout_batches_code")
        op.drop_table("vendor_payout_batches")

    vendor_payout_columns = _table_columns("vendor_payouts")
    if "payout_batch_id" in vendor_payout_columns:
        with op.batch_alter_table("vendor_payouts", schema=None) as batch_op:
            if "ix_vendor_payouts_payout_batch_id" in _table_indexes("vendor_payouts"):
                batch_op.drop_index("ix_vendor_payouts_payout_batch_id")
            batch_op.drop_column("payout_batch_id")

    vendor_document_columns = _table_columns("vendor_documents")
    if vendor_document_columns:
        with op.batch_alter_table("vendor_documents", schema=None) as batch_op:
            if "ix_vendor_documents_reviewed_by_user_id" in _table_indexes("vendor_documents"):
                batch_op.drop_index("ix_vendor_documents_reviewed_by_user_id")
            if "ix_vendor_documents_is_current" in _table_indexes("vendor_documents"):
                batch_op.drop_index("ix_vendor_documents_is_current")
            if "review_reason_history_json" in vendor_document_columns:
                batch_op.drop_column("review_reason_history_json")
            if "resubmission_requested_at" in vendor_document_columns:
                batch_op.drop_column("resubmission_requested_at")
            if "reviewed_by_user_id" in vendor_document_columns:
                batch_op.drop_column("reviewed_by_user_id")
            if "is_current" in vendor_document_columns:
                batch_op.drop_column("is_current")
            if "version" in vendor_document_columns:
                batch_op.drop_column("version")

    bank_account_columns = _table_columns("vendor_bank_accounts")
    if "remarks" in bank_account_columns:
        with op.batch_alter_table("vendor_bank_accounts", schema=None) as batch_op:
            batch_op.drop_column("remarks")

    vendor_columns = _table_columns("vendors")
    if vendor_columns:
        with op.batch_alter_table("vendors", schema=None) as batch_op:
            if "ix_vendors_kyc_assigned_reviewer_user_id" in _table_indexes("vendors"):
                batch_op.drop_index("ix_vendors_kyc_assigned_reviewer_user_id")
            if "ix_vendors_kyc_last_reviewer_user_id" in _table_indexes("vendors"):
                batch_op.drop_index("ix_vendors_kyc_last_reviewer_user_id")
            if "ix_vendors_kyc_status" in _table_indexes("vendors"):
                batch_op.drop_index("ix_vendors_kyc_status")
            if "verification_timeline_json" in vendor_columns:
                batch_op.drop_column("verification_timeline_json")
            if "kyc_review_reasons_json" in vendor_columns:
                batch_op.drop_column("kyc_review_reasons_json")
            if "kyc_reviewer_assigned_at" in vendor_columns:
                batch_op.drop_column("kyc_reviewer_assigned_at")
            if "kyc_assigned_reviewer_user_id" in vendor_columns:
                batch_op.drop_column("kyc_assigned_reviewer_user_id")
            if "kyc_last_reviewer_user_id" in vendor_columns:
                batch_op.drop_column("kyc_last_reviewer_user_id")
            if "kyc_reviewed_at" in vendor_columns:
                batch_op.drop_column("kyc_reviewed_at")
            if "kyc_review_started_at" in vendor_columns:
                batch_op.drop_column("kyc_review_started_at")
            if "kyc_submitted_at" in vendor_columns:
                batch_op.drop_column("kyc_submitted_at")
            if "kyc_status" in vendor_columns:
                batch_op.drop_column("kyc_status")
            if "onboarding_step" in vendor_columns:
                batch_op.drop_column("onboarding_step")

    op.execute("DROP TYPE IF EXISTS vendorkycstatus")

    _rename_enum_value("vendorstatus", "pending", "PENDING")
    _rename_enum_value("vendorstatus", "approved", "APPROVED")
    _rename_enum_value("vendorstatus", "rejected", "REJECTED")
    _rename_enum_value("vendorstatus", "suspended", "SUSPENDED")

    _rename_enum_value("commissiontier", "standard", "STANDARD")
    _rename_enum_value("commissiontier", "premium", "PREMIUM")
    _rename_enum_value("commissiontier", "enterprise", "ENTERPRISE")

    _rename_enum_value("bankaccountverificationstatus", "pending", "PENDING")
    _rename_enum_value("bankaccountverificationstatus", "verified", "VERIFIED")
    _rename_enum_value("bankaccountverificationstatus", "failed", "FAILED")

    _rename_enum_value("vendordocumentstatus", "submitted", "PENDING")
    _rename_enum_value("vendordocumentstatus", "verified", "VERIFIED")
    _rename_enum_value("vendordocumentstatus", "rejected", "REJECTED")

    _rename_enum_value("vendorpayoutstatus", "pending", "PENDING")
    _rename_enum_value("vendorpayoutstatus", "processing", "PROCESSING")
    _rename_enum_value("vendorpayoutstatus", "paid", "PAID")
    _rename_enum_value("vendorpayoutstatus", "failed", "FAILED")
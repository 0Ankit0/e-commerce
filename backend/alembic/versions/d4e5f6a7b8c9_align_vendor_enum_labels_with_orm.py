"""align_vendor_enum_labels_with_orm

Revision ID: d4e5f6a7b8c9
Revises: c3d4e5f6a7b8
Create Date: 2026-05-29 02:15:00.000000

"""

from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "d4e5f6a7b8c9"
down_revision: Union[str, Sequence[str], None] = "c3d4e5f6a7b8"
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


def _to_upper_labels(enum_name: str, mapping: dict[str, str]) -> None:
    for old_value, new_value in mapping.items():
        _rename_enum_value(enum_name, old_value, new_value)


def upgrade() -> None:
    """Upgrade schema."""
    _to_upper_labels(
        "vendorstatus",
        {
            "pending": "PENDING",
            "approved": "APPROVED",
            "rejected": "REJECTED",
            "suspended": "SUSPENDED",
            "needs_resubmission": "NEEDS_RESUBMISSION",
            "under_review": "UNDER_REVIEW",
        },
    )
    _add_enum_value("vendorstatus", "NEEDS_RESUBMISSION")
    _add_enum_value("vendorstatus", "UNDER_REVIEW")

    _to_upper_labels(
        "commissiontier",
        {
            "standard": "STANDARD",
            "premium": "PREMIUM",
            "enterprise": "ENTERPRISE",
        },
    )

    _to_upper_labels(
        "bankaccountverificationstatus",
        {
            "pending": "PENDING",
            "verified": "VERIFIED",
            "failed": "FAILED",
        },
    )

    _to_upper_labels(
        "vendordocumentstatus",
        {
            "submitted": "SUBMITTED",
            "under_review": "UNDER_REVIEW",
            "needs_resubmission": "NEEDS_RESUBMISSION",
            "verified": "VERIFIED",
            "rejected": "REJECTED",
        },
    )
    _add_enum_value("vendordocumentstatus", "SUBMITTED")
    _add_enum_value("vendordocumentstatus", "UNDER_REVIEW")
    _add_enum_value("vendordocumentstatus", "NEEDS_RESUBMISSION")
    _add_enum_value("vendordocumentstatus", "VERIFIED")
    _add_enum_value("vendordocumentstatus", "REJECTED")

    _to_upper_labels(
        "vendorpayoutstatus",
        {
            "requested": "REQUESTED",
            "pending": "PENDING",
            "processing": "PROCESSING",
            "paid": "PAID",
            "failed": "FAILED",
        },
    )
    _add_enum_value("vendorpayoutstatus", "REQUESTED")

    _to_upper_labels(
        "vendorkycstatus",
        {
            "submitted": "SUBMITTED",
            "under_review": "UNDER_REVIEW",
            "resubmission_required": "RESUBMISSION_REQUIRED",
            "approved": "APPROVED",
            "rejected": "REJECTED",
            "suspended_after_approval": "SUSPENDED_AFTER_APPROVAL",
        },
    )
    _add_enum_value("vendorkycstatus", "SUBMITTED")
    _add_enum_value("vendorkycstatus", "UNDER_REVIEW")
    _add_enum_value("vendorkycstatus", "RESUBMISSION_REQUIRED")
    _add_enum_value("vendorkycstatus", "APPROVED")
    _add_enum_value("vendorkycstatus", "REJECTED")
    _add_enum_value("vendorkycstatus", "SUSPENDED_AFTER_APPROVAL")


def downgrade() -> None:
    """Downgrade schema."""
    _to_upper_labels(
        "vendorstatus",
        {
            "PENDING": "pending",
            "APPROVED": "approved",
            "REJECTED": "rejected",
            "SUSPENDED": "suspended",
            "NEEDS_RESUBMISSION": "needs_resubmission",
            "UNDER_REVIEW": "under_review",
        },
    )

    _to_upper_labels(
        "commissiontier",
        {
            "STANDARD": "standard",
            "PREMIUM": "premium",
            "ENTERPRISE": "enterprise",
        },
    )

    _to_upper_labels(
        "bankaccountverificationstatus",
        {
            "PENDING": "pending",
            "VERIFIED": "verified",
            "FAILED": "failed",
        },
    )

    _to_upper_labels(
        "vendordocumentstatus",
        {
            "SUBMITTED": "submitted",
            "UNDER_REVIEW": "under_review",
            "NEEDS_RESUBMISSION": "needs_resubmission",
            "VERIFIED": "verified",
            "REJECTED": "rejected",
        },
    )

    _to_upper_labels(
        "vendorpayoutstatus",
        {
            "REQUESTED": "requested",
            "PENDING": "pending",
            "PROCESSING": "processing",
            "PAID": "paid",
            "FAILED": "failed",
        },
    )

    _to_upper_labels(
        "vendorkycstatus",
        {
            "SUBMITTED": "submitted",
            "UNDER_REVIEW": "under_review",
            "RESUBMISSION_REQUIRED": "resubmission_required",
            "APPROVED": "approved",
            "REJECTED": "rejected",
            "SUSPENDED_AFTER_APPROVAL": "suspended_after_approval",
        },
    )
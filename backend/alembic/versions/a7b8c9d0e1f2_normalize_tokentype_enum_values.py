"""normalize_tokentype_enum_values

Revision ID: a7b8c9d0e1f2
Revises: f1c2e3d4b5a6
Create Date: 2026-05-21 15:05:00.000000

"""

from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "a7b8c9d0e1f2"
down_revision: Union[str, Sequence[str], None] = "f1c2e3d4b5a6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _rename_enum_value(old_value: str, new_value: str) -> None:
    op.execute(
        f"""
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1
                FROM pg_type t
                JOIN pg_enum e ON t.oid = e.enumtypid
                WHERE t.typname = 'tokentype' AND e.enumlabel = '{old_value}'
            ) AND NOT EXISTS (
                SELECT 1
                FROM pg_type t
                JOIN pg_enum e ON t.oid = e.enumtypid
                WHERE t.typname = 'tokentype' AND e.enumlabel = '{new_value}'
            ) THEN
                ALTER TYPE tokentype RENAME VALUE '{old_value}' TO '{new_value}';
            END IF;
        END
        $$;
        """
    )


def upgrade() -> None:
    """Upgrade schema."""
    _rename_enum_value("ACCESS", "access")
    _rename_enum_value("REFRESH", "refresh")
    _rename_enum_value("PASSWORD_RESET", "password_reset")
    _rename_enum_value("EMAIL_VERIFICATION", "email_verification")
    _rename_enum_value("TEMP_AUTH", "temp_auth")
    _rename_enum_value("BEARER", "bearer")
    _rename_enum_value("IP_WHITELIST", "ip_whitelist")
    _rename_enum_value("IP_BLACKLIST", "ip_blacklist")


def downgrade() -> None:
    """Downgrade schema."""
    _rename_enum_value("access", "ACCESS")
    _rename_enum_value("refresh", "REFRESH")
    _rename_enum_value("password_reset", "PASSWORD_RESET")
    _rename_enum_value("email_verification", "EMAIL_VERIFICATION")
    _rename_enum_value("temp_auth", "TEMP_AUTH")
    _rename_enum_value("bearer", "BEARER")
    _rename_enum_value("ip_whitelist", "IP_WHITELIST")
    _rename_enum_value("ip_blacklist", "IP_BLACKLIST")
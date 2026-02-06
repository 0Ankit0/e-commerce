from hashid_field import rest
from rest_framework import serializers

from apps.vendors.models import BankAccount


class BankAccountSerializer(serializers.ModelSerializer):
    id = rest.HashidSerializerCharField(source_field="vendors.BankAccount.id", read_only=True)
    vendor_id = rest.HashidSerializerCharField(source_field="vendors.Vendor.id", source="vendor.id", read_only=True)

    class Meta:
        model = BankAccount
        fields = (
            "id",
            "vendor_id",
            "account_name",
            "account_number",
            "ifsc_code",
            "bank_name",
            "is_primary",
            "verification_status",
        )
        read_only_fields = ("verification_status",)

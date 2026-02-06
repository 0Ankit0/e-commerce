from hashid_field import rest
from rest_framework import serializers

from apps.vendors.models import Vendor


class VendorSerializer(serializers.ModelSerializer):
    id = rest.HashidSerializerCharField(source_field="vendors.Vendor.id", read_only=True)

    class Meta:
        model = Vendor
        fields = (
            "id",
            "business_name",
            "display_name",
            "slug",
            "description",
            "logo",
            "banner",
            "gstin",
            "pan",
            "status",
            "rating",
            "rating_count",
            "product_count",
            "commission_tier",
            "approved_at",
        )
        read_only_fields = ("slug", "status", "rating", "rating_count", "product_count", "approved_at")

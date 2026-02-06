from hashid_field import rest
from rest_framework import serializers

from apps.users.models import Address


class AddressSerializer(serializers.ModelSerializer):
    id = rest.HashidSerializerCharField(source_field="users.Address.id", read_only=True)

    class Meta:
        model = Address
        fields = (
            "id",
            "name",
            "phone",
            "line1",
            "line2",
            "city",
            "state",
            "pincode",
            "country",
            "landmark",
            "type",
            "is_default",
            "latitude",
            "longitude",
        )

from hashid_field import rest
from rest_framework import serializers
from apps.inventory.models import Warehouse

class WarehouseSerializer(serializers.ModelSerializer):
    id = rest.HashidSerializerCharField(source_field="inventory.Warehouse.id", read_only=True)
    vendor_id = rest.HashidSerializerCharField(source_field="vendors.Vendor.id", source="vendor.id", read_only=True)
    
    class Meta:
        model = Warehouse
        fields = (
            "id", "vendor_id", "name", "address", "city", "state", "pincode",
            "contact_phone", "latitude", "longitude", "is_default", "is_active"
        )

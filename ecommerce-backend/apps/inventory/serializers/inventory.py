from hashid_field import rest
from rest_framework import serializers
from apps.inventory.models import Inventory

class InventorySerializer(serializers.ModelSerializer):
    id = rest.HashidSerializerCharField(source_field="inventory.Inventory.id", read_only=True)
    variant_id = rest.HashidSerializerCharField(source_field="catalog.ProductVariant.id", source="variant.id", read_only=True)
    warehouse_id = rest.HashidSerializerCharField(source_field="inventory.Warehouse.id", source="warehouse.id", read_only=True)
    variant_name = serializers.CharField(source="variant.name", read_only=True)
    warehouse_name = serializers.CharField(source="warehouse.name", read_only=True)
    
    class Meta:
        model = Inventory
        fields = (
            "id", "variant_id", "warehouse_id", "variant_name", "warehouse_name",
            "quantity", "reserved_qty", "reorder_level", "reorder_qty", 
            "last_restocked_at"
        )

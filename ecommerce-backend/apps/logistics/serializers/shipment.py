from hashid_field import rest
from rest_framework import serializers
from apps.logistics.models import Shipment

class ShipmentSerializer(serializers.ModelSerializer):
    id = rest.HashidSerializerCharField(source_field="logistics.Shipment.id", read_only=True)
    order_id = rest.HashidSerializerCharField(source_field="orders.Order.id", source="order.id", read_only=True)
    vendor_order_id = rest.HashidSerializerCharField(source_field="orders.VendorOrder.id", source="vendor_order.id", read_only=True)
    vendor_id = rest.HashidSerializerCharField(source_field="vendors.Vendor.id", source="vendor.id", read_only=True)
    
    class Meta:
        model = Shipment
        fields = (
            "id", "awb", "order_id", "vendor_order_id", "vendor_id", 
            "warehouse", "branch", "agent", "status", "type", 
            "weight", "dimensions", "declared_value", "is_cod", 
            "cod_amount", "picked_up_at", "delivered_at"
        )
        read_only_fields = ("awb", "status", "picked_up_at", "delivered_at")

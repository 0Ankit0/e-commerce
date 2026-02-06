from hashid_field import rest
from rest_framework import serializers
from apps.orders.models import VendorOrder
from .order_item import OrderItemSerializer

class VendorOrderSerializer(serializers.ModelSerializer):
    id = rest.HashidSerializerCharField(source_field="orders.VendorOrder.id", read_only=True)
    order_id = rest.HashidSerializerCharField(source_field="orders.Order.id", source="order.id", read_only=True)
    vendor_id = rest.HashidSerializerCharField(source_field="vendors.Vendor.id", source="vendor.id", read_only=True)
    items = OrderItemSerializer(many=True, read_only=True)
    
    class Meta:
        model = VendorOrder
        fields = (
            "id", "order_id", "vendor_id", "vendor_order_number", 
            "status", "subtotal", "commission", "vendor_amount", 
            "accepted_at", "packed_at", "items"
        )

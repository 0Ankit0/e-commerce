from hashid_field import rest
from rest_framework import serializers
from apps.orders.models import Order
from apps.users.serializers import AddressSerializer
from .order_item import OrderItemSerializer

class OrderSerializer(serializers.ModelSerializer):
    id = rest.HashidSerializerCharField(source_field="orders.Order.id", read_only=True)
    user_id = rest.HashidSerializerCharField(source_field="users.User.id", source="user.id", read_only=True)
    address = AddressSerializer(read_only=True)
    items = OrderItemSerializer(many=True, read_only=True)
    
    class Meta:
        model = Order
        fields = (
            "id", "order_number", "user_id", "address", "status",
            "payment_method", "payment_status", "subtotal", "discount",
            "shipping_charge", "tax", "total", "notes", "confirmed_at",
            "shipped_at", "delivered_at", "cancelled_at", "items"
        )

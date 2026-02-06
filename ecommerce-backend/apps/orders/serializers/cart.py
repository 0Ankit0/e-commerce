from hashid_field import rest
from rest_framework import serializers
from apps.orders.models import Cart
from .cart_item import CartItemSerializer

class CartSerializer(serializers.ModelSerializer):
    id = rest.HashidSerializerCharField(source_field="orders.Cart.id", read_only=True)
    items = CartItemSerializer(many=True, read_only=True)
    
    class Meta:
        model = Cart
        fields = ("id", "user", "session_id", "items")
        read_only_fields = ("user", "session_id")

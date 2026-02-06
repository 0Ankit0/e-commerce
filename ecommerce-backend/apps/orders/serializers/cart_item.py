from hashid_field import rest
from rest_framework import serializers
from apps.orders.models import CartItem
from apps.catalog.serializers import ProductVariantSerializer

class CartItemSerializer(serializers.ModelSerializer):
    id = rest.HashidSerializerCharField(source_field="orders.CartItem.id", read_only=True)
    variant = ProductVariantSerializer(read_only=True)
    variant_id = rest.HashidSerializerCharField(source_field="catalog.ProductVariant.id", source="variant.id", write_only=True)
    
    class Meta:
        model = CartItem
        fields = ("id", "variant", "variant_id", "quantity", "price_at_add")

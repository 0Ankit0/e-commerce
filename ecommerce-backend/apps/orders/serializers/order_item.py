from hashid_field import rest
from rest_framework import serializers
from apps.orders.models import OrderItem

class OrderItemSerializer(serializers.ModelSerializer):
    id = rest.HashidSerializerCharField(source_field="orders.OrderItem.id", read_only=True)
    order_id = rest.HashidSerializerCharField(source_field="orders.Order.id", source="order.id", read_only=True)
    product_id = rest.HashidSerializerCharField(source_field="catalog.Product.id", source="product.id", read_only=True)
    variant_id = rest.HashidSerializerCharField(source_field="catalog.ProductVariant.id", source="variant.id", read_only=True)
    vendor_id = rest.HashidSerializerCharField(source_field="vendors.Vendor.id", source="vendor.id", read_only=True)
    
    class Meta:
        model = OrderItem
        fields = (
            "id", "order_id", "product_id", "variant_id", "vendor_id",
            "product_name", "variant_name", "image_url", "quantity",
            "unit_price", "total_price", "status"
        )

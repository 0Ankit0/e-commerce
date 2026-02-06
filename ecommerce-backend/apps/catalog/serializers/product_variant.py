from hashid_field import rest
from rest_framework import serializers
from apps.catalog.models import ProductVariant

class ProductVariantSerializer(serializers.ModelSerializer):
    id = rest.HashidSerializerCharField(source_field="catalog.ProductVariant.id", read_only=True)
    
    class Meta:
        model = ProductVariant
        fields = (
            "id", "sku", "name", "mrp", "selling_price", "cost_price",
            "attributes", "weight", "dimensions", "is_default", "is_active"
        )

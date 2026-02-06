from hashid_field import rest
from rest_framework import serializers

from apps.catalog.models import ProductImage


class ProductImageSerializer(serializers.ModelSerializer):
    id = rest.HashidSerializerCharField(source_field="catalog.ProductImage.id", read_only=True)

    class Meta:
        model = ProductImage
        fields = ("id", "image", "thumbnail", "alt_text", "position", "is_primary")

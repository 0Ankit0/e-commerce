from hashid_field import rest
from rest_framework import serializers
from apps.catalog.models import Product
from .product_image import ProductImageSerializer
from .product_variant import ProductVariantSerializer

class ProductSerializer(serializers.ModelSerializer):
    id = rest.HashidSerializerCharField(source_field="catalog.Product.id", read_only=True)
    vendor_id = rest.HashidSerializerCharField(source_field="vendors.Vendor.id", source="vendor.id", read_only=True)
    category_id = rest.HashidSerializerCharField(source_field="catalog.Category.id", source="category.id", read_only=True)
    brand_id = rest.HashidSerializerCharField(source_field="catalog.Brand.id", source="brand.id", required=False, allow_null=True)
    
    images = ProductImageSerializer(many=True, read_only=True)
    variants = ProductVariantSerializer(many=True, read_only=True)
    
    class Meta:
        model = Product
        fields = (
            "id", "vendor_id", "category_id", "brand_id", "name", "slug",
            "short_description", "description", "specifications", "status",
            "avg_rating", "review_count", "view_count", "is_featured",
            "seo_data", "published_at", "images", "variants"
        )
        read_only_fields = ("slug", "avg_rating", "review_count", "view_count")

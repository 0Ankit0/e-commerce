from hashid_field import rest
from rest_framework import serializers
from apps.catalog.models import Review

class ReviewSerializer(serializers.ModelSerializer):
    id = rest.HashidSerializerCharField(source_field="catalog.Review.id", read_only=True)
    product_id = rest.HashidSerializerCharField(source_field="catalog.Product.id", source="product.id", read_only=True)
    user_name = serializers.CharField(source="user.profile.full_name", read_only=True)
    
    class Meta:
        model = Review
        fields = (
            "id", "product_id", "user_name", "rating", "title", "content",
            "images", "status", "helpful_count", "created"
        )
        read_only_fields = ("status", "helpful_count", "created")

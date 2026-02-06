from hashid_field import rest
from rest_framework import serializers
from apps.catalog.models import Brand

class BrandSerializer(serializers.ModelSerializer):
    id = rest.HashidSerializerCharField(source_field="catalog.Brand.id", read_only=True)
    
    class Meta:
        model = Brand
        fields = ("id", "name", "slug", "logo", "description", "is_active")
        read_only_fields = ("slug",)

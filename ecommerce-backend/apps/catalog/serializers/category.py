from hashid_field import rest
from rest_framework import serializers
from apps.catalog.models import Category

class CategorySerializer(serializers.ModelSerializer):
    id = rest.HashidSerializerCharField(source_field="catalog.Category.id", read_only=True)
    parent_id = rest.HashidSerializerCharField(source_field="catalog.Category.id", source="parent.id", read_only=True)
    
    # Recursive field for children? Or separate endpoint. Let's keep it simple for now.
    
    class Meta:
        model = Category
        fields = (
            "id", "parent_id", "name", "slug", "level", "description",
            "icon", "image", "sort_order", "is_active", "attributes"
        )
        read_only_fields = ("slug", "level")

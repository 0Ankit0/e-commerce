from hashid_field import rest
from rest_framework import serializers
from apps.logistics.models import Hub

class HubSerializer(serializers.ModelSerializer):
    id = rest.HashidSerializerCharField(source_field="logistics.Hub.id", read_only=True)
    
    class Meta:
        model = Hub
        fields = (
            "id", "name", "code", "type", "address", "city", 
            "state", "pincode", "latitude", "longitude", 
            "contact_phone", "is_active"
        )
        read_only_fields = ("code",)

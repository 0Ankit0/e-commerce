from hashid_field import rest
from rest_framework import serializers
from apps.logistics.models import DeliveryAgent

class DeliveryAgentSerializer(serializers.ModelSerializer):
    id = rest.HashidSerializerCharField(source_field="logistics.DeliveryAgent.id", read_only=True)
    branch_id = rest.HashidSerializerCharField(source_field="logistics.Branch.id", source="branch.id", read_only=True)
    user_id = rest.HashidSerializerCharField(source_field="users.User.id", source="user.id", read_only=True)
    user_email = serializers.EmailField(source="user.email", read_only=True)
    
    class Meta:
        model = DeliveryAgent
        fields = (
            "id", "branch_id", "user_id", "user_email", "vehicle_number", 
            "vehicle_type", "status", "capacity", "current_load", 
            "current_lat", "current_lng", "last_location_at"
        )
        read_only_fields = ("current_load", "last_location_at")

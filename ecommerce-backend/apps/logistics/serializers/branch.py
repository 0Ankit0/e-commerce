from hashid_field import rest
from rest_framework import serializers
from apps.logistics.models import Branch

class BranchSerializer(serializers.ModelSerializer):
    id = rest.HashidSerializerCharField(source_field="logistics.Branch.id", read_only=True)
    hub_id = rest.HashidSerializerCharField(source_field="logistics.Hub.id", source="hub.id", read_only=True)
    
    class Meta:
        model = Branch
        fields = (
            "id", "hub_id", "name", "code", "address", "service_pincodes", 
            "contact_phone", "agent_capacity", "is_active"
        )
        read_only_fields = ("code",)

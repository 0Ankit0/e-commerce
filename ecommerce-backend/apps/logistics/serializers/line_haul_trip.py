from hashid_field import rest
from rest_framework import serializers
from apps.logistics.models import LineHaulTrip

class LineHaulTripSerializer(serializers.ModelSerializer):
    id = rest.HashidSerializerCharField(source_field="logistics.LineHaulTrip.id", read_only=True)
    origin_hub_name = serializers.CharField(source="origin_hub.name", read_only=True)
    dest_hub_name = serializers.CharField(source="dest_hub.name", read_only=True)
    
    class Meta:
        model = LineHaulTrip
        fields = (
            "id", "trip_number", "origin_hub", "dest_hub", 
            "origin_hub_name", "dest_hub_name", "vehicle_number", 
            "driver_name", "status", "package_count", "total_weight", 
            "scheduled_departure", "actual_departure", 
            "scheduled_arrival", "actual_arrival"
        )
        read_only_fields = ("trip_number",)

from hashid_field import rest
from rest_framework import serializers
from apps.logistics.models import ShipmentTracking

class ShipmentTrackingSerializer(serializers.ModelSerializer):
    id = rest.HashidSerializerCharField(source_field="logistics.ShipmentTracking.id", read_only=True)
    shipment_awb = serializers.CharField(source="shipment.awb", read_only=True)
    
    class Meta:
        model = ShipmentTracking
        fields = (
            "id", "shipment_awb", "status", "location", "remarks", 
            "latitude", "longitude", "timestamp"
        )
        read_only_fields = ("timestamp",)

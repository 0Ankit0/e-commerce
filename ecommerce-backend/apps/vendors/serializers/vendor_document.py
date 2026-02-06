from hashid_field import rest
from rest_framework import serializers
from apps.vendors.models import VendorDocument

class VendorDocumentSerializer(serializers.ModelSerializer):
    id = rest.HashidSerializerCharField(source_field="vendors.VendorDocument.id", read_only=True)
    vendor_id = rest.HashidSerializerCharField(source_field="vendors.Vendor.id", source="vendor.id", read_only=True)
    
    class Meta:
        model = VendorDocument
        fields = ("id", "vendor_id", "doc_type", "doc_number", "file", "status", "remarks", "verified_at")
        read_only_fields = ("status", "remarks", "verified_at")

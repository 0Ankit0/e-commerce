import hashid_field
from django.db import models
from common.models import TimestampedMixin
from common.storages import PublicS3Boto3StorageWithCDN, UniqueFilePathGenerator
from .vendor import Vendor

class VendorDocument(TimestampedMixin, models.Model):
    id = hashid_field.HashidAutoField(primary_key=True)
    vendor = models.ForeignKey(Vendor, on_delete=models.CASCADE, related_name="documents")
    
    DOC_TYPE_CHOICES = (
        ('gst', 'GST Certificate'),
        ('pan', 'PAN Card'),
        ('cancel_cheque', 'Cancelled Cheque'),
        ('other', 'Other'),
    )
    doc_type = models.CharField(max_length=50, choices=DOC_TYPE_CHOICES)
    doc_number = models.CharField(max_length=100, blank=True)
    file = models.FileField(
        storage=PublicS3Boto3StorageWithCDN,
        upload_to=UniqueFilePathGenerator("vendors/documents")
    )
    
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('verified', 'Verified'),
        ('rejected', 'Rejected'),
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    remarks = models.TextField(blank=True)
    verified_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.vendor.business_name} - {self.doc_type}"

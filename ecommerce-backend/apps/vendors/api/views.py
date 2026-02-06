from rest_framework import viewsets, permissions
from apps.vendors.models import Vendor, VendorDocument, BankAccount
from apps.vendors.serializers import (
    VendorSerializer, 
    VendorDocumentSerializer, 
    BankAccountSerializer
)

class VendorViewSet(viewsets.ModelViewSet):
    queryset = Vendor.objects.all()
    serializer_class = VendorSerializer
    permission_classes = [permissions.IsAuthenticated]
    lookup_field = "slug"

class VendorDocumentViewSet(viewsets.ModelViewSet):
    queryset = VendorDocument.objects.all()
    serializer_class = VendorDocumentSerializer
    permission_classes = [permissions.IsAuthenticated]

class BankAccountViewSet(viewsets.ModelViewSet):
    queryset = BankAccount.objects.all()
    serializer_class = BankAccountSerializer
    permission_classes = [permissions.IsAuthenticated]

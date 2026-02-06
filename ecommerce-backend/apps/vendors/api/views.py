from rest_framework import permissions, viewsets

from apps.vendors.models import BankAccount, Vendor, VendorDocument
from apps.vendors.serializers import BankAccountSerializer, VendorDocumentSerializer, VendorSerializer


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

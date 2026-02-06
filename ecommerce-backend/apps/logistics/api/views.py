from rest_framework import permissions, viewsets

from apps.logistics.models import Branch, DeliveryAgent, Hub, LineHaulTrip, Return, Shipment, ShipmentTracking
from apps.logistics.serializers import (
    BranchSerializer,
    DeliveryAgentSerializer,
    HubSerializer,
    LineHaulTripSerializer,
    ReturnSerializer,
    ShipmentSerializer,
    ShipmentTrackingSerializer,
)


class HubViewSet(viewsets.ModelViewSet):
    queryset = Hub.objects.all()
    serializer_class = HubSerializer
    permission_classes = [permissions.IsAuthenticated]


class BranchViewSet(viewsets.ModelViewSet):
    queryset = Branch.objects.all()
    serializer_class = BranchSerializer
    permission_classes = [permissions.IsAuthenticated]


class DeliveryAgentViewSet(viewsets.ModelViewSet):
    queryset = DeliveryAgent.objects.all()
    serializer_class = DeliveryAgentSerializer
    permission_classes = [permissions.IsAuthenticated]


class ShipmentViewSet(viewsets.ModelViewSet):
    queryset = Shipment.objects.all()
    serializer_class = ShipmentSerializer
    permission_classes = [permissions.IsAuthenticated]


class ShipmentTrackingViewSet(viewsets.ModelViewSet):
    queryset = ShipmentTracking.objects.all()
    serializer_class = ShipmentTrackingSerializer
    permission_classes = [permissions.IsAuthenticated]


class LineHaulTripViewSet(viewsets.ModelViewSet):
    queryset = LineHaulTrip.objects.all()
    serializer_class = LineHaulTripSerializer
    permission_classes = [permissions.IsAuthenticated]


class ReturnViewSet(viewsets.ModelViewSet):
    queryset = Return.objects.all()
    serializer_class = ReturnSerializer
    permission_classes = [permissions.IsAuthenticated]

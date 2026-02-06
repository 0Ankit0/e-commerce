from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'hubs', views.HubViewSet)
router.register(r'branches', views.BranchViewSet)
router.register(r'delivery-agents', views.DeliveryAgentViewSet)
router.register(r'shipments', views.ShipmentViewSet)
router.register(r'tracking', views.ShipmentTrackingViewSet)
router.register(r'trips', views.LineHaulTripViewSet)
router.register(r'returns', views.ReturnViewSet)

urlpatterns = [
    path('', include(router.urls)),
]

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter()
router.register(r"carts", views.CartViewSet, basename="cart")
router.register(r"cart-items", views.CartItemViewSet, basename="cart-item")
router.register(r"orders", views.OrderViewSet, basename="order")
router.register(r"vendor-orders", views.VendorOrderViewSet, basename="vendor-order")
router.register(r"order-items", views.OrderItemViewSet, basename="order-item")

urlpatterns = [
    path("", include(router.urls)),
]

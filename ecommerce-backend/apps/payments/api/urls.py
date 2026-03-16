from django.urls import include, path
from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter()
router.register(r"payments", views.PaymentViewSet)
router.register(r"refunds", views.RefundViewSet)

urlpatterns = [
    path("payments/create/", views.PaymentViewSet.as_view({"post": "create_payment"}), name="payments-create"),
    path("payments/verify/", views.PaymentViewSet.as_view({"post": "verify_payment"}), name="payments-verify"),
    path("payments/webhook/", views.PaymentViewSet.as_view({"post": "gateway_webhook"}), name="payments-webhook"),
    path("", include(router.urls)),
]

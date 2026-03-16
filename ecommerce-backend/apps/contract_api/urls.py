from django.urls import include, path
from rest_framework.routers import DefaultRouter

from . import views

product_router = DefaultRouter()
product_router.register(r"", views.ContractProductViewSet, basename="contract-product")

cart_router = DefaultRouter()
cart_router.register(r"", views.ContractCartViewSet, basename="contract-cart")

order_router = DefaultRouter()
order_router.register(r"", views.ContractOrderViewSet, basename="contract-order")

payment_router = DefaultRouter()
payment_router.register(r"", views.ContractPaymentViewSet, basename="contract-payment")

vendor_router = DefaultRouter()
vendor_router.register(r"", views.ContractVendorViewSet, basename="contract-vendor")
vendor_router.register(r"orders", views.ContractVendorOrderViewSet, basename="contract-vendor-order")

recommendation_router = DefaultRouter()
recommendation_router.register(r"", views.RecommendationViewSet, basename="contract-recommendation")

profile_router = DefaultRouter()
profile_router.register(r"profile", views.ContractProfileViewSet, basename="contract-profile")

urlpatterns = [
    path(
        "auth/",
        include(
            [
                path("signup/", views.ContractSignupView.as_view(), name="contract-signup"),
                path("token-refresh/", views.ContractTokenRefreshView.as_view(), name="contract-token-refresh"),
                path("logout/", views.ContractLogoutView.as_view(), name="contract-logout"),
                path("", include(profile_router.urls)),
            ]
        ),
    ),
    path("products/", include(product_router.urls)),
    path("cart/", include(cart_router.urls)),
    path("orders/", include(order_router.urls)),
    path("payments/", include(payment_router.urls)),
    path("vendor/", include(vendor_router.urls)),
    path("admin/refunds/", views.ContractAdminRefundView.as_view(), name="contract-admin-refunds"),
    path("recommendations/", include(recommendation_router.urls)),
]

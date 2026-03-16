from rest_framework import permissions, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.catalog.api.views import ProductViewSet
from apps.catalog.models import Product
from apps.orders.api.views import CartViewSet, OrderViewSet, VendorOrderViewSet
from apps.payments.api.views import PaymentViewSet
from apps.users import views as user_views
from apps.vendors.api.views import VendorViewSet
from apps.finances.views_admin import AdminRefundView

from .serializers import (
    ContractCartSerializer,
    ContractOrderSerializer,
    ContractPaymentSerializer,
    ContractProductSerializer,
    ContractVendorSerializer,
)


class ContractProductViewSet(ProductViewSet):
    serializer_class = ContractProductSerializer


class ContractCartViewSet(CartViewSet):
    serializer_class = ContractCartSerializer


class ContractOrderViewSet(OrderViewSet):
    serializer_class = ContractOrderSerializer


class ContractPaymentViewSet(PaymentViewSet):
    serializer_class = ContractPaymentSerializer


class ContractVendorViewSet(VendorViewSet):
    serializer_class = ContractVendorSerializer


class RecommendationViewSet(viewsets.ReadOnlyModelViewSet):
    """Simple recommendation adapter on top of product inventory."""

    serializer_class = ContractProductSerializer
    permission_classes = [permissions.AllowAny]

    def get_queryset(self):
        return Product.objects.order_by("-is_featured", "-avg_rating", "-review_count")

    @action(detail=False, methods=["get"], url_path="for-you")
    def for_you(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())[:10]
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)


# Auth/Admin adapters
ContractSignupView = user_views.UserSignupView
ContractTokenRefreshView = user_views.CookieTokenRefreshView
ContractLogoutView = user_views.LogoutView
ContractProfileViewSet = user_views.UserProfileViewSet
ContractAdminRefundView = AdminRefundView
ContractVendorOrderViewSet = VendorOrderViewSet

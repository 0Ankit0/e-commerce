from rest_framework import serializers

from apps.catalog.serializers import ProductSerializer
from apps.orders.serializers import CartSerializer, OrderSerializer
from apps.payments.serializers import PaymentSerializer
from apps.vendors.serializers import VendorSerializer


class ContractProductSerializer(ProductSerializer):
    """Contract serializer with public-facing field names."""

    product_id = serializers.CharField(source="id", read_only=True)

    class Meta(ProductSerializer.Meta):
        fields = (
            "product_id",
            "name",
            "slug",
            "short_description",
            "description",
            "status",
            "avg_rating",
            "review_count",
            "is_featured",
            "published_at",
            "images",
            "variants",
        )


class ContractCartSerializer(CartSerializer):
    """Contract serializer normalizing user/session fields."""

    cart_id = serializers.CharField(source="id", read_only=True)
    user_id = serializers.CharField(source="user.id", read_only=True)

    class Meta(CartSerializer.Meta):
        fields = ("cart_id", "user_id", "session_id", "items")


class ContractOrderSerializer(OrderSerializer):
    """Contract serializer where number and totals are grouped."""

    order_id = serializers.CharField(source="id", read_only=True)
    number = serializers.CharField(source="order_number", read_only=True)
    total_amount = serializers.DecimalField(source="total", max_digits=12, decimal_places=2, read_only=True)

    class Meta(OrderSerializer.Meta):
        fields = (
            "order_id",
            "number",
            "status",
            "payment_status",
            "subtotal",
            "discount",
            "shipping_charge",
            "tax",
            "total_amount",
            "confirmed_at",
            "shipped_at",
            "delivered_at",
            "items",
        )


class ContractPaymentSerializer(PaymentSerializer):
    """Contract serializer with public payment aliases."""

    payment_id = serializers.CharField(source="id", read_only=True)
    state = serializers.CharField(source="status", read_only=True)

    class Meta(PaymentSerializer.Meta):
        fields = (
            "payment_id",
            "order_id",
            "gateway",
            "method",
            "state",
            "amount",
            "currency",
            "authorized_at",
            "captured_at",
            "failure_reason",
        )


class ContractVendorSerializer(VendorSerializer):
    """Contract serializer exposing canonical vendor fields."""

    vendor_id = serializers.CharField(source="id", read_only=True)
    name = serializers.CharField(source="display_name", read_only=True)

    class Meta(VendorSerializer.Meta):
        fields = (
            "vendor_id",
            "name",
            "business_name",
            "slug",
            "description",
            "status",
            "rating",
            "product_count",
            "approved_at",
        )


class RecommendationSerializer(serializers.Serializer):
    """Contract response payload for recommendations endpoint."""

    product_id = serializers.CharField(read_only=True)
    name = serializers.CharField(read_only=True)
    slug = serializers.CharField(read_only=True)
    score = serializers.FloatField(read_only=True)

from rest_framework import serializers


class CouponApplySerializer(serializers.Serializer):
    code = serializers.CharField(max_length=50)


class OrderActionResponseSerializer(serializers.Serializer):
    status = serializers.CharField()
    message = serializers.CharField()


class OrderTrackingSerializer(serializers.Serializer):
    order_number = serializers.CharField()
    status = serializers.CharField()
    phase = serializers.CharField()
    shipped_at = serializers.CharField(allow_null=True)
    delivered_at = serializers.CharField(allow_null=True)


class OrderInvoiceSerializer(serializers.Serializer):
    invoice_number = serializers.CharField()
    order_number = serializers.CharField()
    issued_at = serializers.CharField()
    subtotal = serializers.CharField()
    discount = serializers.CharField()
    tax = serializers.CharField()
    shipping_charge = serializers.CharField()
    total = serializers.CharField()
    item_count = serializers.IntegerField()

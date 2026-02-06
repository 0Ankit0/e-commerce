from hashid_field import rest
from rest_framework import serializers

from apps.payments.models import Payment


class PaymentSerializer(serializers.ModelSerializer):
    id = rest.HashidSerializerCharField(source_field="payments.Payment.id", read_only=True)
    order_id = rest.HashidSerializerCharField(source_field="orders.Order.id", source="order.id", read_only=True)

    class Meta:
        model = Payment
        fields = (
            "id",
            "order_id",
            "gateway_order_id",
            "gateway_payment_id",
            "gateway",
            "method",
            "status",
            "amount",
            "currency",
            "gateway_response",
            "failure_reason",
            "authorized_at",
            "captured_at",
        )

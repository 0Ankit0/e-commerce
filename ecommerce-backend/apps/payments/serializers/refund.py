from hashid_field import rest
from rest_framework import serializers

from apps.payments.models import Refund


class RefundSerializer(serializers.ModelSerializer):
    id = rest.HashidSerializerCharField(source_field="payments.Refund.id", read_only=True)
    payment_id = rest.HashidSerializerCharField(source_field="payments.Payment.id", source="payment.id", read_only=True)

    class Meta:
        model = Refund
        fields = (
            "id",
            "payment_id",
            "gateway_refund_id",
            "amount",
            "reason",
            "status",
            "method",
            "gateway_response",
            "processed_at",
        )

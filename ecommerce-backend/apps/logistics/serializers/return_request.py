from hashid_field import rest
from rest_framework import serializers

from apps.logistics.models import Return


class ReturnSerializer(serializers.ModelSerializer):
    id = rest.HashidSerializerCharField(source_field="logistics.Return.id", read_only=True)
    order_id = rest.HashidSerializerCharField(source_field="orders.Order.id", source="order.id", read_only=True)
    order_item_id = rest.HashidSerializerCharField(
        source_field="orders.OrderItem.id", source="order_item.id", read_only=True
    )

    class Meta:
        model = Return
        fields = (
            "id",
            "return_number",
            "order_id",
            "order_item_id",
            "status",
            "reason",
            "reason_text",
            "images",
            "refund_amount",
            "reverse_shipment",
            "approved_at",
            "completed_at",
        )
        read_only_fields = ("return_number", "approved_at", "completed_at")

from rest_framework import serializers

from apps.catalog.models import Product
from apps.catalog.serializers.product import ProductSerializer
from apps.recommendations.models import RecommendationEvent


class RecommendationsQuerySerializer(serializers.Serializer):
    type = serializers.ChoiceField(choices=["similar", "trending", "personalized"], required=False, default="similar")
    productId = serializers.IntegerField(required=False)
    limit = serializers.IntegerField(required=False, min_value=1, max_value=50, default=10)

    def validate_productId(self, value: int) -> int:
        if not Product.objects.filter(id=value).exists():
            raise serializers.ValidationError("Invalid productId.")
        return value


class RecommendationEventSerializer(serializers.Serializer):
    productId = serializers.IntegerField()
    eventType = serializers.ChoiceField(choices=RecommendationEvent.EventType.choices)
    metadata = serializers.JSONField(required=False, default=dict)

    def validate_productId(self, value: int) -> int:
        if not Product.objects.filter(id=value).exists():
            raise serializers.ValidationError("Invalid productId.")
        return value


class RecommendationsResponseSerializer(serializers.Serializer):
    type = serializers.CharField()
    productId = serializers.IntegerField(required=False, allow_null=True)
    recommendations = ProductSerializer(many=True)

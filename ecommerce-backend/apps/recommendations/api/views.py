from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.catalog.serializers.product import ProductSerializer
from apps.recommendations.serializers import RecommendationEventSerializer, RecommendationsQuerySerializer
from apps.recommendations.services import RecommendationService


class RecommendationsView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        query_serializer = RecommendationsQuerySerializer(data=request.query_params)
        query_serializer.is_valid(raise_exception=True)
        data = query_serializer.validated_data

        recommendation_type = data.get("type", "similar")
        product_id = data.get("productId")
        limit = data.get("limit", 10)

        recommendations = RecommendationService.get_recommendations(
            recommendation_type=recommendation_type,
            product_id=product_id,
            limit=limit,
        )
        return Response(
            {
                "type": recommendation_type,
                "productId": product_id,
                "recommendations": ProductSerializer(recommendations, many=True).data,
            },
            status=status.HTTP_200_OK,
        )


class RecommendationEventView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = RecommendationEventSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        RecommendationService.capture_event(
            user=request.user,
            product_id=serializer.validated_data["productId"],
            event_type=serializer.validated_data["eventType"],
            metadata=serializer.validated_data.get("metadata", {}),
        )
        return Response({"status": "accepted"}, status=status.HTTP_202_ACCEPTED)

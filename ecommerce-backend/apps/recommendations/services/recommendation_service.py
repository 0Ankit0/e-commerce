from apps.catalog.models import Product
from apps.recommendations.models import RecommendationEvent
from apps.recommendations.tasks import process_recommendation_event


class RecommendationService:
    @staticmethod
    def get_recommendations(*, recommendation_type: str, product_id: int | None, limit: int):
        queryset = Product.objects.filter(status="published")

        if recommendation_type == "similar" and product_id:
            target = Product.objects.filter(id=product_id).select_related("category").first()
            if target:
                queryset = queryset.filter(category=target.category).exclude(id=target.id)
            else:
                queryset = queryset.exclude(id=product_id)
        elif recommendation_type == "trending":
            queryset = queryset.order_by("-created_at")
        elif recommendation_type == "personalized":
            queryset = queryset.order_by("-updated_at")

        return queryset[:limit]

    @staticmethod
    def capture_event(*, user, product_id: int, event_type: str, metadata: dict):
        event = RecommendationEvent.objects.create(
            user=user if user and user.is_authenticated else None,
            product_id=product_id,
            event_type=event_type,
            metadata=metadata,
        )
        process_recommendation_event.delay(event.id)
        return event

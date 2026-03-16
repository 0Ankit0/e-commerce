from django.urls import path

from .views import RecommendationEventView, RecommendationsView

urlpatterns = [
    path("", RecommendationsView.as_view(), name="recommendations"),
    path("events", RecommendationEventView.as_view(), name="recommendation-events"),
]

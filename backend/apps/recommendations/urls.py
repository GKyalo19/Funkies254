"""Routes mounted under /api/."""

from django.urls import path

from apps.recommendations.views import RecommendationFeedView

urlpatterns = [
    path("recommendations/feed/", RecommendationFeedView.as_view(), name="recommendation-feed"),
]

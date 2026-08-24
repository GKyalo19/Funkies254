"""Routes mounted under /api/."""

from django.urls import path

from apps.preferences.views import MyPreferenceView

urlpatterns = [
    path("preferences/me/", MyPreferenceView.as_view(), name="preference-me"),
]

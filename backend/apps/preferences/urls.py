from django.urls import path

from .views import MyPreferenceView

urlpatterns = [
    path("me/", MyPreferenceView.as_view(), name="preferences-me"),
]

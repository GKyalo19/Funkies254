"""Routes mounted under /api/."""

from django.urls import path

from apps.events.views import (
    CategoryListView,
    EventDetailView,
    EventListCreateView,
    EventRegistrationListView,
    EventSaveView,
    EventVerifyView,
    SavedEventListView,
    SchoolLevelListView,
)

urlpatterns = [
    path("categories/", CategoryListView.as_view(), name="category-list"),
    path("school-levels/", SchoolLevelListView.as_view(), name="school-level-list"),
    path("events/", EventListCreateView.as_view(), name="event-list"),
    path("users/me/saved-events/", SavedEventListView.as_view(), name="saved-event-list"),
    path("events/<str:identifier>/save/", EventSaveView.as_view(), name="event-save"),
    path("events/<str:identifier>/verify/", EventVerifyView.as_view(), name="event-verify"),
    path(
        "events/<str:identifier>/registrations/",
        EventRegistrationListView.as_view(),
        name="event-registration-list",
    ),
    path("events/<str:identifier>/", EventDetailView.as_view(), name="event-detail"),
]

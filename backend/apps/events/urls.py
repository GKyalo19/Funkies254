"""Routes mounted under /api/."""

from django.urls import path

from apps.events.views import (
    CategoryListView,
    EventClickOutView,
    EventDetailView,
    EventListCreateView,
    EventRegistrationListView,
    EventSaveView,
    EventVerifyView,
    SavedEventListView,
    SchoolLevelListView,
    SectionListView,
)

urlpatterns = [
    path("categories/", CategoryListView.as_view(), name="category-list"),
    path("sections/", SectionListView.as_view(), name="section-list"),
    path("school-levels/", SchoolLevelListView.as_view(), name="school-level-list"),
    path("events/", EventListCreateView.as_view(), name="event-list"),
    path("users/me/saved-events/", SavedEventListView.as_view(), name="saved-event-list"),
    path("events/<str:identifier>/save/", EventSaveView.as_view(), name="event-save"),
    path("events/<str:identifier>/click-out/", EventClickOutView.as_view(), name="event-click-out"),
    path("events/<str:identifier>/verify/", EventVerifyView.as_view(), name="event-verify"),
    path(
        "events/<str:identifier>/registrations/",
        EventRegistrationListView.as_view(),
        name="event-registration-list",
    ),
    path("events/<str:identifier>/", EventDetailView.as_view(), name="event-detail"),
]

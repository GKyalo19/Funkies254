"""Routes mounted under /api/."""

from django.urls import path

from apps.registrations.views import (
    MyRegistrationListView,
    RegistrationCancelView,
    RegistrationCreateView,
    RegistrationDetailView,
    RegistrationStatusView,
)

urlpatterns = [
    path("registrations/", RegistrationCreateView.as_view(), name="registration-create"),
    path(
        "users/me/registrations/",
        MyRegistrationListView.as_view(),
        name="my-registration-list",
    ),
    path("registrations/<uuid:pk>/", RegistrationDetailView.as_view(), name="registration-detail"),
    path(
        "registrations/<uuid:pk>/cancel/",
        RegistrationCancelView.as_view(),
        name="registration-cancel",
    ),
    path(
        "registrations/<uuid:pk>/status/",
        RegistrationStatusView.as_view(),
        name="registration-status",
    ),
]

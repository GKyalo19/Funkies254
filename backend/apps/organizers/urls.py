"""Routes mounted under /api/."""

from django.urls import path

from apps.organizers.views import (
    InstitutionDetailView,
    InstitutionListCreateView,
    InstitutionVerifyView,
)

urlpatterns = [
    path("institutions/", InstitutionListCreateView.as_view(), name="institution-list"),
    path("institutions/<slug:slug>/", InstitutionDetailView.as_view(), name="institution-detail"),
    path(
        "institutions/<slug:slug>/verify/",
        InstitutionVerifyView.as_view(),
        name="institution-verify",
    ),
]

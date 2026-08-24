"""Root URL configuration — REST API surface described in docs/API.md."""

from django.contrib import admin
from django.http import JsonResponse
from django.urls import include, path


def health(_request):
    return JsonResponse({"status": "ok", "service": "funkies254-api"})


urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/health/", health, name="health"),
    path("api/auth/", include("apps.users.auth_urls")),
    path("api/", include("apps.common.urls")),
    path("api/", include("apps.users.urls")),
    path("api/", include("apps.organizers.urls")),
    path("api/", include("apps.events.urls")),
    path("api/", include("apps.registrations.urls")),
    path("api/", include("apps.preferences.urls")),
    path("api/", include("apps.recommendations.urls")),
]

"""
Top-level URL routing.

Every API route is namespaced under /api/... so the frontend only ever needs
to know one base URL. Each app owns its own `urls.py`; this file just wires
the prefixes together. See docs/API.md for the full endpoint reference.
"""
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path


urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/auth/", include("apps.users.auth_urls")),
    path("api/users/", include("apps.users.urls")),
    path("api/organizers/", include("apps.organizers.urls")),
    path("api/events/", include("apps.events.urls")),
    path("api/registrations/", include("apps.registrations.urls")),
    path("api/preferences/", include("apps.preferences.urls")),
    path("api/recommendations/", include("apps.recommendations.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

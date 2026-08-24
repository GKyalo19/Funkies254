"""Routes mounted under /api/."""

from django.urls import path

from apps.common.views import AdminActivityLogListView

urlpatterns = [
    path(
        "admin/activity-logs/",
        AdminActivityLogListView.as_view(),
        name="admin-activity-log-list",
    ),
]

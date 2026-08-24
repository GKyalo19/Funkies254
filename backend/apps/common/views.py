"""Shared admin-facing endpoints (§14)."""

from rest_framework import generics

from apps.common.models import AdminActivityLog
from apps.common.permissions import IsAdmin
from apps.common.serializers import AdminActivityLogSerializer


class AdminActivityLogListView(generics.ListAPIView):
    """Read-only audit trail for the admin dashboard."""

    serializer_class = AdminActivityLogSerializer
    permission_classes = (IsAdmin,)
    queryset = AdminActivityLog.objects.select_related("user").all()
    filterset_fields = ("action", "table_name", "record_id", "user")
    ordering_fields = ("created_at", "action")
    ordering = ("-created_at",)

"""Preference endpoints — a user may only read and write their own row (§9)."""

from rest_framework import generics
from rest_framework.permissions import IsAuthenticated

from apps.preferences.models import UserPreference
from apps.preferences.serializers import UserPreferenceSerializer


class MyPreferenceView(generics.RetrieveUpdateAPIView):
    """GET/PATCH /api/preferences/me/"""

    serializer_class = UserPreferenceSerializer
    permission_classes = (IsAuthenticated,)
    http_method_names = ("get", "patch", "head", "options")

    def get_object(self):
        preference, _ = UserPreference.objects.get_or_create(user=self.request.user)
        return preference

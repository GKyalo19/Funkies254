from rest_framework import generics, permissions

from .models import UserPreference
from .serializers import UserPreferenceSerializer


class MyPreferenceView(generics.RetrieveUpdateAPIView):
    """GET/PUT/PATCH /api/preferences/me/ — created on first access with sensible defaults."""

    serializer_class = UserPreferenceSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        preference, _created = UserPreference.objects.get_or_create(user=self.request.user)
        return preference

from rest_framework import permissions, viewsets

from .models import Registration
from .serializers import RegistrationSerializer


class RegistrationViewSet(viewsets.ModelViewSet):
    """
    /api/registrations/       GET (my registrations), POST (register for an event)
    /api/registrations/{id}/  DELETE (cancel) — soft-deletes by marking status=cancelled
    """

    serializer_class = RegistrationSerializer
    permission_classes = [permissions.IsAuthenticated]
    http_method_names = ["get", "post", "delete", "head", "options"]

    def get_queryset(self):
        return Registration.objects.filter(user=self.request.user).select_related("event", "event__organizer")

    def perform_destroy(self, instance):
        instance.status = "cancelled"
        instance.save(update_fields=["status"])

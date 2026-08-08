from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.common.permissions import IsStaffOrReadOnly

from .models import Follow, Organizer
from .serializers import OrganizerSerializer


class OrganizerViewSet(viewsets.ModelViewSet):
    """
    /api/organizers/                 GET (list), POST (staff only)
    /api/organizers/{slug}/          GET, PATCH/PUT, DELETE (staff only)
    /api/organizers/{slug}/follow/   POST (follow), DELETE (unfollow)
    """

    # `followers_count` is a model @property (computed via .count()), not a DB
    # column — annotating a queryset field with the same name would collide
    # with the property setter-less descriptor, so we deliberately don't.
    queryset = Organizer.objects.all().order_by("name")
    serializer_class = OrganizerSerializer
    permission_classes = [IsStaffOrReadOnly]
    lookup_field = "slug"
    search_fields = ["name", "description"]

    @action(detail=True, methods=["post", "delete"], permission_classes=[permissions.IsAuthenticated])
    def follow(self, request, slug=None):
        organizer = self.get_object()

        if request.method == "POST":
            Follow.objects.get_or_create(user=request.user, organizer=organizer)
            return Response({"detail": f"Now following {organizer.name}."}, status=status.HTTP_200_OK)

        Follow.objects.filter(user=request.user, organizer=organizer).delete()
        return Response({"detail": f"Unfollowed {organizer.name}."}, status=status.HTTP_200_OK)

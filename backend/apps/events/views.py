from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.common.permissions import IsStaffOrReadOnly
from apps.common.supabase_storage import SupabaseStorageError, upload_file

from .filters import EventFilter
from .models import Category, Event
from .serializers import CategorySerializer, EventDetailSerializer, EventListSerializer, EventWriteSerializer


class CategoryViewSet(viewsets.ModelViewSet):
    """/api/events/categories/ — read-only for everyone, staff manage the taxonomy."""

    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = [IsStaffOrReadOnly]
    pagination_class = None


class EventViewSet(viewsets.ModelViewSet):
    """
    /api/events/                GET (filterable list), POST (staff)
    /api/events/{slug}/         GET, PATCH/PUT, DELETE (staff)
    /api/events/{slug}/similar/ GET — other events sharing a category
    /api/events/{slug}/cover-image/ POST (staff) — multipart upload
    """

    queryset = Event.objects.select_related("organizer").prefetch_related("categories").all()
    permission_classes = [IsStaffOrReadOnly]
    lookup_field = "slug"
    filterset_class = EventFilter
    search_fields = ["title", "description", "venue_name", "location"]
    ordering_fields = ["start_datetime", "registration_fee", "created_at"]

    def get_queryset(self):
        queryset = super().get_queryset()
        # Non-staff visitors should never see drafts/cancelled events.
        if not (self.request.user and self.request.user.is_staff):
            queryset = queryset.filter(status="published")
        return queryset

    def get_serializer_class(self):
        if self.action in ("create", "update", "partial_update"):
            return EventWriteSerializer
        if self.action == "retrieve":
            return EventDetailSerializer
        return EventListSerializer

    @action(detail=True, methods=["get"])
    def similar(self, request, slug=None):
        event = self.get_object()
        category_ids = event.categories.values_list("id", flat=True)
        similar_events = (
            Event.objects.filter(categories__in=category_ids, status="published")
            .exclude(pk=event.pk)
            .exclude(start_datetime__lt=timezone.now())
            .distinct()[:6]
        )
        serializer = EventListSerializer(similar_events, many=True, context={"request": request})
        return Response(serializer.data)

    @action(detail=True, methods=["post"], url_path="cover-image", permission_classes=[IsStaffOrReadOnly])
    def cover_image(self, request, slug=None):
        event = self.get_object()
        file_obj = request.FILES.get("cover_image")
        if not file_obj:
            return Response({"detail": "No file provided under the 'cover_image' field."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            public_url = upload_file(file_obj, folder="events/covers")
        except SupabaseStorageError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_502_BAD_GATEWAY)

        event.cover_image_url = public_url
        event.save(update_fields=["cover_image_url"])
        return Response(EventDetailSerializer(event, context={"request": request}).data)

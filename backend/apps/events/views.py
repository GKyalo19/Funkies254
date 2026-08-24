"""Event, taxonomy and saved-event endpoints (§9)."""

import uuid

from django.shortcuts import get_object_or_404
from rest_framework import generics, status
from rest_framework.exceptions import PermissionDenied
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.common.permissions import IsAdmin, IsEventOwner, IsStaffOrReadOnly, IsStudent
from apps.events.filters import EventFilter
from apps.events.models import Category, Event, SavedEvent, SchoolLevel
from apps.events.serializers import (
    CategorySerializer,
    EventSerializer,
    EventWriteSerializer,
    SavedEventSerializer,
    SchoolLevelSerializer,
)
from apps.events.services import (
    create_event,
    delete_event,
    save_event,
    set_event_verified,
    unsave_event,
    update_event,
)


class _EventContextMixin:
    """Adds the per-user saved/registered id sets so lists avoid N+1 queries."""

    def get_serializer_context(self):
        context = super().get_serializer_context()
        user = self.request.user
        if user and user.is_authenticated:
            from apps.registrations.models import EventRegistration

            context["saved_event_ids"] = set(
                SavedEvent.objects.filter(user=user).values_list("event_id", flat=True)
            )
            context["registered_event_ids"] = set(
                EventRegistration.objects.filter(
                    user=user, status=EventRegistration.ACTIVE_STATUS
                ).values_list("event_id", flat=True)
            )
        return context


class CategoryListView(generics.ListAPIView):
    """Reference taxonomy used by event forms and preference pickers (§18)."""

    serializer_class = CategorySerializer
    queryset = Category.objects.all()
    permission_classes = (AllowAny,)
    pagination_class = None
    search_fields = ("name", "slug")


class SchoolLevelListView(generics.ListAPIView):
    serializer_class = SchoolLevelSerializer
    queryset = SchoolLevel.objects.all()
    permission_classes = (AllowAny,)
    pagination_class = None


class EventListCreateView(_EventContextMixin, generics.ListCreateAPIView):
    permission_classes = (IsStaffOrReadOnly,)
    parser_classes = (JSONParser, MultiPartParser, FormParser)
    filterset_class = EventFilter
    search_fields = ("title", "description", "venue", "location")
    ordering_fields = ("start_time", "end_time", "created_at", "title")
    ordering = ("start_time",)

    def get_serializer_class(self):
        return EventWriteSerializer if self.request.method == "POST" else EventSerializer

    def get_queryset(self):
        queryset = Event.objects.with_related().visible_to(self.request.user)
        if self.request.query_params.get("mine") in ("true", "1", "yes"):
            user = self.request.user
            if not user.is_authenticated:
                raise PermissionDenied("Authentication is required to list your own events.")
            queryset = queryset.filter(created_by=user)
        return queryset

    def create(self, request, *args, **kwargs):
        serializer = EventWriteSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)

        payload = dict(serializer.validated_data)
        event = create_event(
            actor=request.user,
            categories=payload.pop("categories", None),
            cover_image=payload.pop("cover_image", None),
            **payload,
        )
        event = Event.objects.with_related().get(pk=event.pk)
        return Response(
            EventSerializer(event, context=self.get_serializer_context()).data,
            status=status.HTTP_201_CREATED,
        )


class EventDetailView(_EventContextMixin, generics.RetrieveUpdateDestroyAPIView):
    """Detail route accepts either the event slug or its UUID."""

    permission_classes = (IsStaffOrReadOnly, IsEventOwner)
    parser_classes = (JSONParser, MultiPartParser, FormParser)
    http_method_names = ("get", "patch", "delete", "head", "options")

    def get_serializer_class(self):
        return EventWriteSerializer if self.request.method == "PATCH" else EventSerializer

    def get_queryset(self):
        return Event.objects.with_related().visible_to(self.request.user)

    def get_object(self):
        identifier = self.kwargs["identifier"]
        queryset = self.get_queryset()
        try:
            lookup = {"pk": uuid.UUID(str(identifier))}
        except (ValueError, AttributeError, TypeError):
            lookup = {"slug": identifier}
        event = get_object_or_404(queryset, **lookup)
        self.check_object_permissions(self.request, event)
        return event

    def update(self, request, *args, **kwargs):
        event = self.get_object()
        serializer = EventWriteSerializer(
            event, data=request.data, partial=True, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)

        payload = dict(serializer.validated_data)
        event = update_event(
            actor=request.user,
            event=event,
            categories=payload.pop("categories", None),
            cover_image=payload.pop("cover_image", None),
            **payload,
        )
        event = Event.objects.with_related().get(pk=event.pk)
        return Response(EventSerializer(event, context=self.get_serializer_context()).data)

    def destroy(self, request, *args, **kwargs):
        delete_event(actor=request.user, event=self.get_object())
        return Response(status=status.HTTP_204_NO_CONTENT)


class EventVerifyView(APIView):
    """Administrator verification of curated content."""

    permission_classes = (IsAdmin,)

    def post(self, request, identifier):
        event = _resolve_event(identifier, Event.objects.all())
        verified = request.data.get("verified", True)
        if isinstance(verified, str):
            verified = verified.lower() not in ("false", "0", "no")
        set_event_verified(actor=request.user, event=event, verified=bool(verified))
        event = Event.objects.with_related().get(pk=event.pk)
        return Response(EventSerializer(event, context={"request": request}).data)


class EventSaveView(APIView):
    """Save/unsave an event for the authenticated student (§10.2)."""

    permission_classes = (IsStudent,)

    def post(self, request, identifier):
        event = _resolve_event(identifier, Event.objects.visible_to(request.user))
        saved, created = save_event(user=request.user, event=event)
        return Response(
            {
                "saved": True,
                "already_saved": not created,
                "event_id": str(event.id),
                "saved_at": saved.saved_at,
            },
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )

    def delete(self, request, identifier):
        event = _resolve_event(identifier, Event.objects.all())
        removed = unsave_event(user=request.user, event=event)
        return Response({"saved": False, "was_saved": removed})


class SavedEventListView(generics.ListAPIView):
    """GET /api/users/me/saved-events/"""

    serializer_class = SavedEventSerializer
    permission_classes = (IsAuthenticated,)
    ordering = ("-saved_at",)

    def get_queryset(self):
        return (
            SavedEvent.objects.filter(user=self.request.user)
            .select_related("event", "event__institution", "event__school_level")
            .prefetch_related("event__categories")
        )


class EventRegistrationListView(generics.ListAPIView):
    """Registrations for one event — visible to the event owner and admins (§6)."""

    permission_classes = (IsAuthenticated, IsEventOwner)

    def get_serializer_class(self):
        from apps.registrations.serializers import EventRegistrationSerializer

        return EventRegistrationSerializer

    def get_queryset(self):
        from apps.registrations.models import EventRegistration

        event = self._event()
        return EventRegistration.objects.filter(event=event).select_related("user", "event")

    def _event(self):
        event = _resolve_event(self.kwargs["identifier"], Event.objects.all())
        # IsEventOwner grants read access to everyone, so ownership for this
        # privileged read is checked explicitly.
        user = self.request.user
        is_owner = event.created_by_id == user.id or (
            user.institution_id and event.institution_id == user.institution_id
        )
        if not (user.is_platform_admin or (user.is_institution_staff and is_owner)):
            raise PermissionDenied("You may only view registrations for your own events.")
        return event


def _resolve_event(identifier, queryset):
    try:
        return get_object_or_404(queryset, pk=uuid.UUID(str(identifier)))
    except (ValueError, AttributeError, TypeError):
        return get_object_or_404(queryset, slug=identifier)

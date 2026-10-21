"""Registration endpoints (§9, §10.3)."""

from rest_framework import generics, status
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.common.permissions import IsStudent
from apps.registrations.models import EventRegistration
from apps.registrations.serializers import (
    EventRegistrationSerializer,
    RegistrationCreateSerializer,
    RegistrationStatusSerializer,
)
from apps.registrations.services import (
    cancel_registration,
    register_for_event,
    set_registration_status,
)


def _registration_queryset():
    return EventRegistration.objects.select_related(
        "user", "event", "event__institution", "event__school_level"
    ).prefetch_related("event__categories")


class RegistrationCreateView(APIView):
    """On-site registration is closed. Visitors register on the organiser's site (EVT-3)."""

    permission_classes = (AllowAny,)

    def post(self, request):
        link = None
        event_id = request.data.get("event_id") if isinstance(request.data, dict) else None
        event_slug = request.data.get("event_slug") if isinstance(request.data, dict) else None
        if event_id or event_slug:
            from django.core.exceptions import ValidationError

            from apps.events.models import Event

            event = None
            try:
                if event_id:
                    event = Event.objects.filter(pk=event_id).first()
                elif event_slug:
                    event = Event.objects.filter(slug=event_slug).first()
            except (ValidationError, ValueError):
                event = None
            if event is not None:
                link = event.registration_link
        return Response(
            {
                "detail": (
                    "On-site registration has closed. Use the organiser's registration link."
                ),
                "code": "registration_external",
                "registration_link": link,
            },
            status=status.HTTP_410_GONE,
        )


class MyRegistrationListView(generics.ListAPIView):
    """GET /api/users/me/registrations/"""

    serializer_class = EventRegistrationSerializer
    permission_classes = (IsAuthenticated,)
    filterset_fields = ("status",)
    ordering_fields = ("registered_at",)
    ordering = ("-registered_at",)

    def get_queryset(self):
        return _registration_queryset().filter(user=self.request.user)


class RegistrationDetailView(generics.RetrieveAPIView):
    serializer_class = EventRegistrationSerializer
    permission_classes = (IsAuthenticated,)

    def get_queryset(self):
        return _visible_registrations(self.request.user)


class RegistrationCancelView(APIView):
    """A student cancels their own registration."""

    permission_classes = (IsAuthenticated,)

    def post(self, request, pk):
        registration = generics.get_object_or_404(
            _registration_queryset(), pk=pk, user=request.user
        )
        cancel_registration(registration=registration)
        return Response(
            EventRegistrationSerializer(registration, context={"request": request}).data
        )


class RegistrationStatusView(APIView):
    """An event owner or admin marks attendance."""

    permission_classes = (IsAuthenticated,)

    def post(self, request, pk):
        registration = generics.get_object_or_404(_registration_queryset(), pk=pk)
        _assert_may_manage(request.user, registration)

        serializer = RegistrationStatusSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        set_registration_status(
            registration=registration, status=serializer.validated_data["status"]
        )
        return Response(
            EventRegistrationSerializer(registration, context={"request": request}).data
        )


def _visible_registrations(user):
    """A student sees their own rows; owners and admins see their events' rows."""
    queryset = _registration_queryset()
    if user.is_platform_admin:
        return queryset
    if user.is_institution_staff:
        from django.db.models import Q

        own = Q(event__created_by=user)
        if user.institution_id:
            own |= Q(event__institution_id=user.institution_id)
        return queryset.filter(own | Q(user=user))
    return queryset.filter(user=user)


def _assert_may_manage(user, registration):
    if user.is_platform_admin:
        return
    event = registration.event
    is_owner = event.created_by_id == user.id or (
        user.institution_id and event.institution_id == user.institution_id
    )
    if not (user.is_institution_staff and is_owner):
        raise PermissionDenied("You may only manage registrations for your own events.")

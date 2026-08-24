"""Registration endpoints (§9, §10.3)."""

from rest_framework import generics, status
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import IsAuthenticated
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
    """POST /api/registrations/ — students register for a visible, open event."""

    permission_classes = (IsStudent,)

    def post(self, request):
        serializer = RegistrationCreateSerializer(
            data=request.data, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)

        registration, created = register_for_event(
            user=request.user, event=serializer.validated_data["event"]
        )
        registration = _registration_queryset().get(pk=registration.pk)
        return Response(
            EventRegistrationSerializer(registration, context={"request": request}).data,
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
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

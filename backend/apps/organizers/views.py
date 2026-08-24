"""Institution endpoints — public read, owner/admin write (§9)."""

from django.db.models import Count, Q
from rest_framework import generics, status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.common.permissions import IsAdmin, IsInstitutionOwner
from apps.organizers.models import Institution
from apps.organizers.serializers import InstitutionSerializer
from apps.organizers.services import (
    create_institution,
    set_institution_verified,
    update_institution,
)


def _institution_queryset():
    return Institution.objects.select_related("created_by").annotate(
        event_count=Count("events", filter=Q(events__is_verified=True), distinct=True)
    )


class InstitutionListCreateView(generics.ListCreateAPIView):
    serializer_class = InstitutionSerializer
    queryset = _institution_queryset()
    filterset_fields = ("verified",)
    search_fields = ("name", "location")
    ordering_fields = ("name", "created_at")
    ordering = ("name",)

    def get_permissions(self):
        if self.request.method == "POST":
            return [IsAdmin()]
        return [AllowAny()]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        institution = create_institution(actor=request.user, **serializer.validated_data)
        return Response(
            self.get_serializer(institution).data, status=status.HTTP_201_CREATED
        )


class InstitutionDetailView(generics.RetrieveUpdateAPIView):
    serializer_class = InstitutionSerializer
    queryset = _institution_queryset()
    lookup_field = "slug"
    http_method_names = ("get", "patch", "head", "options")

    def get_permissions(self):
        if self.request.method in ("PATCH", "PUT"):
            return [IsAuthenticated(), IsInstitutionOwner()]
        return [AllowAny()]

    def update(self, request, *args, **kwargs):
        institution = self.get_object()
        serializer = self.get_serializer(institution, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        institution = update_institution(
            actor=request.user, institution=institution, **serializer.validated_data
        )
        return Response(self.get_serializer(institution).data)


class InstitutionVerifyView(APIView):
    """Admin verification action (§10.4)."""

    permission_classes = (IsAdmin,)

    def post(self, request, slug):
        institution = generics.get_object_or_404(Institution, slug=slug)
        verified = request.data.get("verified", True)
        if isinstance(verified, str):
            verified = verified.lower() not in ("false", "0", "no")
        set_institution_verified(
            actor=request.user, institution=institution, verified=bool(verified)
        )
        institution = _institution_queryset().get(pk=institution.pk)
        return Response(InstitutionSerializer(institution).data)

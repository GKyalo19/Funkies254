"""Admin review queue and the latest health report."""

from rest_framework import generics, status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.agent.models import Proposal
from apps.agent.reporting import build_health_report
from apps.agent.serializers import ProposalSerializer
from apps.agent.services import approve_all_pending, approve_proposal, reject_proposal
from apps.common.models import NewsletterSubscriber
from apps.common.permissions import IsAdmin


class ProposalListView(generics.ListAPIView):
    serializer_class = ProposalSerializer
    permission_classes = (IsAdmin,)
    filterset_fields = ("status", "kind")
    ordering = ("-created_at",)

    def get_queryset(self):
        queryset = Proposal.objects.select_related("event", "reviewed_by")
        section = self.request.query_params.get("section")
        if section:
            queryset = queryset.filter(event__categories__section__slug=section).distinct()
        return queryset


class ProposalApproveView(APIView):
    permission_classes = (IsAdmin,)

    def post(self, request, pk):
        proposal = generics.get_object_or_404(Proposal, pk=pk)
        payload = request.data.get("payload")
        approve_proposal(actor=request.user, proposal=proposal, payload_override=payload)
        proposal.refresh_from_db()
        return Response(ProposalSerializer(proposal).data)


class ProposalRejectView(APIView):
    permission_classes = (IsAdmin,)

    def post(self, request, pk):
        proposal = generics.get_object_or_404(Proposal, pk=pk)
        reject_proposal(actor=request.user, proposal=proposal)
        proposal.refresh_from_db()
        return Response(ProposalSerializer(proposal).data)


class ProposalApproveAllView(APIView):
    permission_classes = (IsAdmin,)

    def post(self, request):
        count = approve_all_pending(actor=request.user)
        return Response({"approved": count})


class HealthReportView(APIView):
    permission_classes = (IsAdmin,)

    def get(self, request):
        return Response(build_health_report())


class NewsletterSubscribeView(APIView):
    permission_classes = (AllowAny,)

    def post(self, request):
        email = (request.data.get("email") or "").strip().lower()
        if "@" not in email or "." not in email.split("@")[-1]:
            return Response(
                {"detail": "Enter a valid email address.", "code": "invalid_email"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        NewsletterSubscriber.objects.get_or_create(email=email)
        return Response({"detail": "You're on the list."}, status=status.HTTP_201_CREATED)

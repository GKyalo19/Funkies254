from django.urls import path

from apps.agent.views import (
    HealthReportView,
    NewsletterSubscribeView,
    ProposalApproveAllView,
    ProposalApproveView,
    ProposalListView,
    ProposalRejectView,
)

urlpatterns = [
    path("agent/proposals/", ProposalListView.as_view(), name="agent-proposal-list"),
    path(
        "agent/proposals/approve-all/",
        ProposalApproveAllView.as_view(),
        name="agent-proposal-approve-all",
    ),
    path(
        "agent/proposals/<uuid:pk>/approve/",
        ProposalApproveView.as_view(),
        name="agent-proposal-approve",
    ),
    path(
        "agent/proposals/<uuid:pk>/reject/",
        ProposalRejectView.as_view(),
        name="agent-proposal-reject",
    ),
    path("admin/health-report/latest/", HealthReportView.as_view(), name="health-report"),
    path("newsletter/", NewsletterSubscribeView.as_view(), name="newsletter-subscribe"),
]

"""Sources, proposals and run history for the daily ingestion agent (AGENT-2)."""

from django.conf import settings
from django.db import models

from apps.common.enums import ProposalKind, ProposalStatus, SourceKind
from apps.common.models import UUIDPrimaryKeyModel


class Source(UUIDPrimaryKeyModel):
    name = models.CharField(max_length=200)
    url = models.URLField(max_length=500)
    kind = models.CharField(max_length=16, choices=SourceKind.choices, default=SourceKind.HTML)
    section = models.ForeignKey(
        "events.Section",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="agent_sources",
    )
    needs_browser = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    last_checked_at = models.DateTimeField(null=True, blank=True)
    last_status = models.CharField(max_length=32, blank=True, default="")

    class Meta:
        db_table = "agent_sources"
        ordering = ("name",)

    def __str__(self):
        return self.name


class Proposal(UUIDPrimaryKeyModel):
    kind = models.CharField(max_length=16, choices=ProposalKind.choices)
    event = models.ForeignKey(
        "events.Event",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="proposals",
    )
    payload = models.JSONField(default=dict)
    source_url = models.TextField(blank=True, default="")
    external_mentions = models.PositiveIntegerField(default=0)
    status = models.CharField(
        max_length=16, choices=ProposalStatus.choices, default=ProposalStatus.PENDING
    )
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="proposals_reviewed",
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "agent_proposals"
        ordering = ("-created_at",)
        indexes = [
            models.Index(fields=["status", "created_at"], name="agent_proposal_status_idx"),
        ]

    def __str__(self):
        title = (self.payload or {}).get("title") or self.kind
        return f"{self.kind}: {title}"


class AgentRun(UUIDPrimaryKeyModel):
    started_at = models.DateTimeField(auto_now_add=True)
    finished_at = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=16, default="running")
    stats = models.JSONField(default=dict)
    errors = models.JSONField(default=list)

    class Meta:
        db_table = "agent_runs"
        ordering = ("-started_at",)

    def __str__(self):
        return f"{self.status} {self.started_at}"

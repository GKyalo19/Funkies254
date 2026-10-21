"""Review queue permissions and approval (AGENT-6)."""

from datetime import timedelta

import pytest
from django.utils import timezone

from apps.agent.models import Proposal
from apps.agent.services import approve_proposal, ingest_payloads, reject_proposal
from apps.common.enums import AuditAction, EventSource, ProposalKind
from apps.common.models import AdminActivityLog
from apps.events.models import Event

pytestmark = pytest.mark.django_db


def _payload():
    start = timezone.now() + timedelta(days=10)
    return {
        "title": "Robotics Saturday",
        "description": "A public robotics workshop.",
        "start_time": start.isoformat(),
        "end_time": (start + timedelta(hours=3)).isoformat(),
        "registration_link": "https://events.example.com/robotics",
        "format": "in_person",
        "category_slugs": [],
    }


def test_ingest_queues_a_new_proposal_and_drops_an_exact_duplicate(db):
    first = ingest_payloads([_payload()])
    second = ingest_payloads([_payload()])

    assert first["queued"] == 1
    assert second["duplicates"] == 1
    assert Proposal.objects.count() == 1


def test_admin_approval_publishes_an_agent_event(db, admin_user):
    ingest_payloads([_payload()])
    proposal = Proposal.objects.get()

    approve_proposal(actor=admin_user, proposal=proposal)

    event = Event.objects.get(title="Robotics Saturday")
    assert event.is_verified is True
    assert event.source == EventSource.AGENT
    assert event.verified_by_id == admin_user.id
    assert event.created_by.email == "agent@funkies254.com"
    assert AdminActivityLog.objects.filter(action=AuditAction.APPROVED_PROPOSAL).exists()


def test_reject_is_audited(db, admin_user):
    proposal = Proposal.objects.create(kind=ProposalKind.NEW, payload=_payload(), source_url="https://example.com")

    reject_proposal(actor=admin_user, proposal=proposal)

    proposal.refresh_from_db()
    assert proposal.status == "rejected"
    assert AdminActivityLog.objects.filter(action=AuditAction.REJECTED_PROPOSAL).exists()


def test_student_cannot_open_the_queue(api, student, login):
    login(student)
    assert api.get("/api/agent/proposals/").status_code == 403


def test_admin_can_list_pending_proposals(api, admin_user, login):
    Proposal.objects.create(kind=ProposalKind.NEW, payload=_payload())
    login(admin_user)

    response = api.get("/api/agent/proposals/?status=pending")

    assert response.status_code == 200
    assert response.data["count"] == 1

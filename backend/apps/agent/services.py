"""Proposal review and the daily ingestion run (AGENT-4, AGENT-6)."""

import difflib
from datetime import timedelta

from django.db import transaction
from django.utils import timezone
from django.utils.dateparse import parse_datetime

from apps.agent.models import AgentRun, Proposal
from apps.common.audit import log_action
from apps.common.enums import (
    AuditAction,
    EventFormat,
    EventSource,
    ProposalKind,
    ProposalStatus,
    UserRole,
)
from apps.common.exceptions import BusinessRuleError
from apps.events.models import Category, Event, EventCategory
from apps.events.services import compute_popularity, set_event_verified
from apps.users.models import User

AGENT_EMAIL = "agent@funkies254.com"
MAX_PROPOSALS_PER_RUN = 100


def get_agent_user() -> User:
    user = User.objects.filter(email=AGENT_EMAIL).first()
    if user is not None:
        return user
    user = User.objects.create_user(
        email=AGENT_EMAIL,
        password=None,
        name="Funkies Agent",
        role=UserRole.AGENT,
        email_verified=True,
    )
    user.set_unusable_password()
    user.save(update_fields=["password"])
    return user


def find_duplicate(payload: dict):
    """Match an existing event by registration link, or institution + day + similar title."""
    link = (payload.get("registration_link") or "").strip()
    if link:
        match = Event.objects.filter(registration_link=link).first()
        if match is not None:
            return match

    title = (payload.get("title") or "").strip()
    start = _as_datetime(payload.get("start_time"))
    institution_id = payload.get("institution_id")
    if not title or start is None:
        return None
    day = start.date()
    candidates = Event.objects.filter(start_time__date=day)
    if institution_id:
        candidates = candidates.filter(institution_id=institution_id)
    for event in candidates:
        ratio = difflib.SequenceMatcher(None, event.title.lower(), title.lower()).ratio()
        if ratio >= 0.82:
            return event
    return None


def queue_proposal(*, kind, payload, source_url="", external_mentions=0, event=None) -> Proposal | None:
    pending = Proposal.objects.filter(status=ProposalStatus.PENDING)
    if kind == ProposalKind.NEW and pending.filter(source_url=source_url, payload__title=payload.get("title")).exists():
        return None
    if event is not None and pending.filter(event=event, kind=kind).exists():
        return None
    return Proposal.objects.create(
        kind=kind,
        event=event,
        payload=payload,
        source_url=source_url or "",
        external_mentions=external_mentions or 0,
    )


@transaction.atomic
def approve_proposal(*, actor, proposal: Proposal, payload_override=None) -> Proposal:
    if proposal.status != ProposalStatus.PENDING:
        raise BusinessRuleError("Only a pending proposal can be approved.")

    payload = payload_override or proposal.payload or {}
    agent = get_agent_user()

    if proposal.kind == ProposalKind.NEW:
        event = _create_event_from_payload(payload, agent=agent, source_url=proposal.source_url)
        event.external_mentions = proposal.external_mentions or payload.get("external_mentions") or 0
        event.source = EventSource.AGENT
        event.source_url = proposal.source_url or payload.get("source_url")
        event.save()
        set_event_verified(actor=actor, event=event, verified=True)
        proposal.event = event
    elif proposal.kind == ProposalKind.UPDATE:
        if proposal.event_id is None:
            raise BusinessRuleError("An update proposal needs an event.")
        _apply_update(proposal.event, payload)
        log_action(actor=actor, action=AuditAction.UPDATED_EVENT, instance=proposal.event)
    elif proposal.kind == ProposalKind.UNPUBLISH:
        if proposal.event_id is None:
            raise BusinessRuleError("An unpublish proposal needs an event.")
        set_event_verified(actor=actor, event=proposal.event, verified=False)
    else:
        raise BusinessRuleError("Unknown proposal kind.")

    proposal.status = ProposalStatus.APPROVED
    proposal.reviewed_by = actor
    proposal.reviewed_at = timezone.now()
    if payload_override is not None:
        proposal.payload = payload
    proposal.save()
    log_action(actor=actor, action=AuditAction.APPROVED_PROPOSAL, instance=proposal)
    return proposal


@transaction.atomic
def reject_proposal(*, actor, proposal: Proposal) -> Proposal:
    if proposal.status != ProposalStatus.PENDING:
        raise BusinessRuleError("Only a pending proposal can be rejected.")
    proposal.status = ProposalStatus.REJECTED
    proposal.reviewed_by = actor
    proposal.reviewed_at = timezone.now()
    proposal.save()
    log_action(actor=actor, action=AuditAction.REJECTED_PROPOSAL, instance=proposal)
    return proposal


def approve_all_pending(*, actor) -> int:
    count = 0
    for proposal in Proposal.objects.filter(status=ProposalStatus.PENDING).order_by("created_at"):
        approve_proposal(actor=actor, proposal=proposal)
        count += 1
    return count


def expire_ended_proposals() -> int:
    now = timezone.now()
    expired = 0
    for proposal in Proposal.objects.filter(status=ProposalStatus.PENDING).exclude(event=None):
        if proposal.event.end_time < now:
            proposal.status = ProposalStatus.EXPIRED
            proposal.save(update_fields=["status"])
            expired += 1
    return expired


def ingest_payloads(payloads, *, source_url="") -> dict:
    """Validate and queue agent findings. Used by the run command and tests."""
    stats = {"found": 0, "queued": 0, "duplicates": 0, "invalid": 0}
    for payload in payloads:
        stats["found"] += 1
        if Proposal.objects.filter(status=ProposalStatus.PENDING).count() >= MAX_PROPOSALS_PER_RUN:
            break
        error = _payload_error(payload)
        if error:
            stats["invalid"] += 1
            continue
        existing = find_duplicate(payload)
        if existing is None:
            created = queue_proposal(
                kind=ProposalKind.NEW,
                payload=payload,
                source_url=payload.get("source_url") or source_url,
                external_mentions=payload.get("external_mentions") or 0,
            )
            stats["queued" if created else "duplicates"] += 1
            continue
        if _materially_changed(existing, payload):
            created = queue_proposal(
                kind=ProposalKind.UPDATE,
                payload=payload,
                source_url=payload.get("source_url") or source_url,
                external_mentions=payload.get("external_mentions") or 0,
                event=existing,
            )
            stats["queued" if created else "duplicates"] += 1
        else:
            stats["duplicates"] += 1
    return stats


def finish_run(run: AgentRun, *, stats, errors, failed=False) -> AgentRun:
    compute_popularity()
    expire_ended_proposals()
    from apps.common.models import RequestMetric

    cutoff = timezone.now() - timedelta(days=30)
    RequestMetric.objects.filter(created_at__lt=cutoff).delete()
    run.stats = stats
    run.errors = errors
    run.status = "failed" if failed else "succeeded"
    run.finished_at = timezone.now()
    run.save()
    return run


def _create_event_from_payload(payload, *, agent, source_url) -> Event:
    start = _as_datetime(payload.get("start_time"))
    end = _as_datetime(payload.get("end_time"))
    if start is None or end is None or end <= start:
        raise BusinessRuleError("Proposal is missing a valid start and end time.")
    link = payload.get("registration_link") or ""
    if not str(link).startswith("https://"):
        raise BusinessRuleError("Proposal needs an https:// registration link.")
    event = Event(
        title=payload.get("title") or "Untitled event",
        description=payload.get("description") or "",
        start_time=start,
        end_time=end,
        venue=payload.get("venue") or None,
        location=payload.get("location") or None,
        country=payload.get("country") or "Kenya",
        format=payload.get("format") or EventFormat.IN_PERSON,
        is_free=payload.get("is_free", True),
        cost_note=payload.get("cost_note") or None,
        registration_link=link,
        source=EventSource.AGENT,
        source_url=source_url or None,
        created_by=agent,
        is_verified=False,
    )
    if payload.get("institution_id"):
        event.institution_id = payload["institution_id"]
    if payload.get("school_level_id"):
        event.school_level_id = payload["school_level_id"]
    event.save()
    slugs = payload.get("category_slugs") or []
    categories = list(Category.objects.filter(slug__in=slugs))
    EventCategory.objects.bulk_create(
        [EventCategory(event=event, category=category) for category in categories],
        ignore_conflicts=True,
    )
    log_action(actor=agent, action=AuditAction.CREATED_EVENT, instance=event)
    return event


def _apply_update(event: Event, payload: dict) -> None:
    for field in (
        "title",
        "description",
        "venue",
        "location",
        "country",
        "format",
        "registration_link",
        "cost_note",
        "source_url",
    ):
        if field in payload and payload[field] not in (None, ""):
            setattr(event, field, payload[field])
    if "is_free" in payload:
        event.is_free = bool(payload["is_free"])
    if "external_mentions" in payload:
        event.external_mentions = int(payload["external_mentions"] or 0)
    start = _as_datetime(payload.get("start_time")) if payload.get("start_time") else None
    end = _as_datetime(payload.get("end_time")) if payload.get("end_time") else None
    if start:
        event.start_time = start
    if end:
        event.end_time = end
    event.save()


def _payload_error(payload: dict) -> str | None:
    if not payload.get("title"):
        return "missing title"
    start = _as_datetime(payload.get("start_time"))
    end = _as_datetime(payload.get("end_time"))
    if start is None or end is None or end <= timezone.now() or end <= start:
        return "event is not upcoming"
    link = payload.get("registration_link") or ""
    if not str(link).startswith("https://"):
        return "registration link"
    return None


def _materially_changed(event: Event, payload: dict) -> bool:
    if payload.get("title") and payload["title"].strip() != event.title:
        return True
    if payload.get("registration_link") and payload["registration_link"] != event.registration_link:
        return True
    if payload.get("description") and payload["description"].strip() != (event.description or "").strip():
        return True
    return False


def _as_datetime(value):
    if value is None or value == "":
        return None
    if hasattr(value, "tzinfo"):
        return value
    parsed = parse_datetime(str(value))
    if parsed is None:
        return None
    if timezone.is_naive(parsed):
        return timezone.make_aware(parsed, timezone.get_current_timezone())
    return parsed

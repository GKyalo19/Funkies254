"""Daily site-health report (AGENT-7)."""

from datetime import timedelta

from django.conf import settings
from django.core.mail import send_mail
from django.db.models import Avg, Count
from django.utils import timezone

from apps.agent.models import AgentRun, Proposal
from apps.common.enums import ADMIN_ROLES, InteractionKind, ProposalKind, ProposalStatus, UserRole
from apps.common.models import RequestMetric
from apps.events.models import EventInteraction, SavedEvent, SearchQuery
from apps.users.models import User


def build_health_report() -> dict:
    now = timezone.now()
    day_ago = now - timedelta(hours=24)
    metrics = RequestMetric.objects.filter(created_at__gte=day_ago)
    total = metrics.count()
    errors = metrics.filter(status_code__gte=500).count()
    durations = list(metrics.values_list("duration_ms", flat=True))
    durations.sort()
    p95 = durations[max(int(len(durations) * 0.95) - 1, 0)] if durations else 0
    average = metrics.aggregate(avg=Avg("duration_ms"))["avg"] or 0

    slowest = list(
        metrics.values("path")
        .annotate(avg=Avg("duration_ms"))
        .order_by("-avg")[:5]
    )
    pending = Proposal.objects.filter(status=ProposalStatus.PENDING)
    by_kind = {
        row["kind"]: row["n"]
        for row in pending.values("kind").annotate(n=Count("id"))
    }
    latest_run = AgentRun.objects.order_by("-started_at").first()
    searches = SearchQuery.objects.filter(created_at__gte=day_ago)
    top_searches = list(
        searches.values("query").annotate(n=Count("id")).order_by("-n")[:10]
    )
    zero_results = list(
        searches.filter(results_count=0).values_list("query", flat=True).distinct()[:20]
    )

    return {
        "generated_at": now.isoformat(),
        "awaiting_approval": {
            "total": pending.count(),
            "by_kind": {
                ProposalKind.NEW: by_kind.get(ProposalKind.NEW, 0),
                ProposalKind.UPDATE: by_kind.get(ProposalKind.UPDATE, 0),
                ProposalKind.UNPUBLISH: by_kind.get(ProposalKind.UNPUBLISH, 0),
            },
            "review_url": "/pages/review-queue.html",
        },
        "site_health": {
            "requests": total,
            "server_error_rate": round(errors / total, 4) if total else 0,
            "average_ms": round(average, 1),
            "p95_ms": p95,
            "slowest": [
                {"path": row["path"], "average_ms": round(row["avg"] or 0, 1)} for row in slowest
            ],
            "uptime_note": (
                "Point an external monitor such as UptimeRobot at GET /api/health/ every 5 minutes."
            ),
        },
        "errors": {
            "critical": errors,
            "non_critical": metrics.filter(duration_ms__gt=3000).count(),
        },
        "agent_run": None
        if latest_run is None
        else {
            "status": latest_run.status,
            "started_at": latest_run.started_at.isoformat(),
            "finished_at": latest_run.finished_at.isoformat() if latest_run.finished_at else None,
            "stats": latest_run.stats,
            "errors": latest_run.errors,
        },
        "usage": {
            "new_signups": User.objects.filter(
                created_at__gte=day_ago, role=UserRole.STUDENT
            ).count(),
            "saves": SavedEvent.objects.filter(saved_at__gte=day_ago).count(),
            "click_outs": EventInteraction.objects.filter(
                kind=InteractionKind.CLICK_OUT, created_at__gte=day_ago
            ).count(),
            "top_searches": top_searches,
            "zero_result_searches": zero_results,
        },
    }


def send_health_report() -> int:
    report = build_health_report()
    recipients = list(
        User.objects.filter(role__in=ADMIN_ROLES, is_active=True, email_verified=True)
        .exclude(email="")
        .values_list("email", flat=True)
    )
    if not recipients:
        return 0
    approval = report["awaiting_approval"]
    health = report["site_health"]
    body = "\n".join(
        [
            "Funkies254 daily report",
            "",
            f"Awaiting approval: {approval['total']} "
            f"(new {approval['by_kind']['new']}, "
            f"update {approval['by_kind']['update']}, "
            f"unpublish {approval['by_kind']['unpublish']})",
            "Review queue: https://www.funkies254.com/pages/review-queue.html",
            "",
            f"API requests (24h): {health['requests']}",
            f"Average response: {health['average_ms']} ms",
            f"95th percentile: {health['p95_ms']} ms",
            f"5xx rate: {health['server_error_rate']}",
            "",
            f"New sign-ups: {report['usage']['new_signups']}",
            f"Saves: {report['usage']['saves']}",
            f"Click-outs: {report['usage']['click_outs']}",
            "",
            health["uptime_note"],
        ]
    )
    send_mail(
        subject="Funkies254 daily report",
        message=body,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=recipients,
        fail_silently=True,
    )
    return len(recipients)

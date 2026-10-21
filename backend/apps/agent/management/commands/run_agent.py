"""Daily ingestion. Network fetches are best-effort; review still happens in the queue."""

import traceback

from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.agent.extractors.jsonld import extract_events
from apps.agent.models import AgentRun, Source
from apps.agent.reporting import send_health_report
from apps.agent.services import finish_run, get_agent_user, ingest_payloads


class Command(BaseCommand):
    help = "Find public events and queue them for admin review."

    def add_arguments(self, parser):
        parser.add_argument(
            "--email",
            action="store_true",
            help="Email the daily report to admins when the run finishes.",
        )

    def handle(self, *args, **options):
        get_agent_user()
        run = AgentRun.objects.create(status="running")
        stats = {"sources": 0, "found": 0, "queued": 0, "duplicates": 0, "invalid": 0}
        errors = []
        failed = False
        try:
            for source in Source.objects.filter(is_active=True):
                stats["sources"] += 1
                try:
                    html = _fetch(source.url)
                    payloads = extract_events(html)
                    for payload in payloads:
                        payload.setdefault("source_url", source.url)
                    result = ingest_payloads(payloads, source_url=source.url)
                    for key in ("found", "queued", "duplicates", "invalid"):
                        stats[key] += result[key]
                    source.last_status = "ok"
                except Exception as exc:
                    failed = True
                    source.last_status = "failed"
                    errors.append({"source": source.name, "error": str(exc)})
                source.last_checked_at = timezone.now()
                source.save(update_fields=["last_status", "last_checked_at"])
        except Exception:
            failed = True
            errors.append({"error": traceback.format_exc()[-500:]})

        finish_run(run, stats=stats, errors=errors, failed=failed and stats["queued"] == 0)
        if failed and stats["queued"] == 0:
            send_health_report()
        elif options["email"]:
            send_health_report()
        self.stdout.write(self.style.SUCCESS(f"Agent run {run.status}: {stats}"))


def _fetch(url: str) -> str:
    import httpx

    headers = {
        "User-Agent": "Funkies254Bot/1.0 (+https://www.funkies254.com/pages/about.html)"
    }
    response = httpx.get(url, headers=headers, timeout=20, follow_redirects=True)
    response.raise_for_status()
    return response.text

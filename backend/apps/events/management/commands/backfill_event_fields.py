"""One-off backfill for format, country and source (EVT-5)."""

from django.core.management.base import BaseCommand

from apps.common.enums import EventFormat, EventSource, UserRole
from apps.events.models import Event


class Command(BaseCommand):
    help = "Set format, country and source on existing events and list published events with no registration link."

    def handle(self, *args, **options):
        updated = 0
        for event in Event.objects.select_related("created_by"):
            changed = []
            if event.is_virtual and event.format != EventFormat.ONLINE:
                event.format = EventFormat.ONLINE
                changed.append("format")
            if not event.country:
                event.country = "Kenya"
                changed.append("country")
            source = _source(event)
            if event.source != source:
                event.source = source
                changed.append("source")
            if changed:
                event.save(update_fields=changed + ["is_virtual", "updated_at"])
                updated += 1

        missing = Event.objects.filter(is_verified=True).exclude(
            registration_link__startswith="https://"
        )
        self.stdout.write(self.style.SUCCESS(f"Updated {updated} event(s)."))
        self.stdout.write("Published events missing an https registration link:")
        if not missing.exists():
            self.stdout.write("  none")
            return
        for event in missing:
            self.stdout.write(f"  {event.id}  {event.slug}  {event.title}")


def _source(event) -> str:
    role = getattr(event.created_by, "role", None)
    if role == UserRole.AGENT:
        return EventSource.AGENT
    if role == UserRole.INSTITUTION_STAFF:
        return EventSource.INSTITUTION_STAFF
    return EventSource.ADMIN

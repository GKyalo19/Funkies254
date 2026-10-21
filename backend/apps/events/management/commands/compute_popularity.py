from django.core.management.base import BaseCommand

from apps.events.services import compute_popularity


class Command(BaseCommand):
    help = "Recompute popularity_score from the last 30 days of saves, views and click-outs."

    def handle(self, *args, **options):
        updated = compute_popularity()
        self.stdout.write(self.style.SUCCESS(f"Updated {updated} event score(s)."))

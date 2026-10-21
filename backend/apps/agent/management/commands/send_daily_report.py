from django.core.management.base import BaseCommand

from apps.agent.reporting import send_health_report


class Command(BaseCommand):
    help = "Email the latest site-health report to admins and super admins."

    def handle(self, *args, **options):
        sent = send_health_report()
        self.stdout.write(self.style.SUCCESS(f"Report sent to {sent} admin(s)."))

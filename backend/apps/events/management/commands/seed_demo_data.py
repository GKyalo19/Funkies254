"""
Populates the database with realistic sample data so the frontend has
something to render immediately, and so manual API testing (Postman/curl)
doesn't require creating everything by hand first.

Usage:
    python manage.py seed_demo_data
    python manage.py seed_demo_data --flush   # wipes events/organizers/categories first
"""
from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.events.models import Category, Event
from apps.organizers.models import Organizer
from apps.users.models import User


CATEGORIES = [
    ("Math", "mdi:calculator-variant"),
    ("Science", "mdi:flask"),
    ("Literature", "mdi:book-open-page-variant"),
    ("Volleyball", "mdi:volleyball"),
    ("Rugby", "mdi:rugby"),
    ("Music", "mdi:music-note"),
    ("Debate", "mdi:microphone"),
    ("Technology", "mdi:laptop"),
]

ORGANIZERS = [
    {"name": "Brookside Kenya", "years_hosting": 10, "description": "Community events across Nairobi."},
    {"name": "Mang'u High School", "years_hosting": 25, "description": "Academic and sports events."},
    {"name": "Kenya Science Congress", "years_hosting": 15, "description": "National science competitions."},
]

EVENTS = [
    {
        "title": "64th Annual Math Olympiad",
        "organizer": "Mang'u High School",
        "categories": ["Math"],
        "description": "A regional math competition for high school students, testing algebra, geometry, and problem solving.",
        "venue_name": "Mang'u High School",
        "address": "Thika - Mang'u Rd, Thika, Kenya",
        "location": "Thika",
        "education_level": "high_school",
        "days_from_now": 9,
        "registration_fee": 0,
    },
    {
        "title": "National Science Congress Finals",
        "organizer": "Kenya Science Congress",
        "categories": ["Science", "Technology"],
        "description": "The finals of the national science project competition, open to high school and college students.",
        "venue_name": "Kenyatta International Convention Centre",
        "address": "Nairobi, Kenya",
        "location": "Nairobi",
        "education_level": "both",
        "days_from_now": 21,
        "registration_fee": 500,
    },
    {
        "title": "Inter-School Volleyball Tournament",
        "organizer": "Brookside Kenya",
        "categories": ["Volleyball"],
        "description": "A weekend volleyball tournament between top Nairobi schools.",
        "venue_name": "Nyayo National Stadium",
        "address": "Nairobi, Kenya",
        "location": "Nairobi",
        "education_level": "high_school",
        "days_from_now": 5,
        "registration_fee": 0,
    },
    {
        "title": "Poetry & Spoken Word Night",
        "organizer": "Brookside Kenya",
        "categories": ["Literature", "Music"],
        "description": "An evening of poetry, spoken word, and live music for college students.",
        "venue_name": "PAWA254",
        "address": "Nairobi, Kenya",
        "location": "Nairobi",
        "education_level": "college",
        "days_from_now": 3,
        "registration_fee": 200,
    },
    {
        "title": "High School Rugby 7s",
        "organizer": "Mang'u High School",
        "categories": ["Rugby"],
        "description": "A fast-paced rugby sevens tournament between high schools in Central Kenya.",
        "venue_name": "RFUEA Ground",
        "address": "Nairobi, Kenya",
        "location": "Nairobi",
        "education_level": "high_school",
        "days_from_now": 14,
        "registration_fee": 0,
    },
]


class Command(BaseCommand):
    help = "Seed the database with demo categories, organizers, and events."

    def add_arguments(self, parser):
        parser.add_argument("--flush", action="store_true", help="Delete existing events/organizers/categories first.")

    def handle(self, *args, **options):
        if options["flush"]:
            Event.objects.all().delete()
            Organizer.objects.all().delete()
            Category.objects.all().delete()
            self.stdout.write(self.style.WARNING("Flushed existing events, organizers, and categories."))

        categories_by_name = {}
        for name, icon in CATEGORIES:
            category, _ = Category.objects.get_or_create(name=name, defaults={"icon": icon})
            categories_by_name[name] = category
        self.stdout.write(self.style.SUCCESS(f"Ensured {len(CATEGORIES)} categories."))

        organizers_by_name = {}
        for data in ORGANIZERS:
            organizer, _ = Organizer.objects.get_or_create(name=data["name"], defaults=data)
            organizers_by_name[data["name"]] = organizer
        self.stdout.write(self.style.SUCCESS(f"Ensured {len(ORGANIZERS)} organizers."))

        created_count = 0
        for data in EVENTS:
            if Event.objects.filter(title=data["title"]).exists():
                continue
            event = Event.objects.create(
                title=data["title"],
                organizer=organizers_by_name[data["organizer"]],
                description=data["description"],
                venue_name=data["venue_name"],
                address=data["address"],
                location=data["location"],
                education_level=data["education_level"],
                registration_fee=data["registration_fee"],
                start_datetime=timezone.now() + timedelta(days=data["days_from_now"]),
                is_featured=data["days_from_now"] <= 7,
                status="published",
            )
            event.categories.set([categories_by_name[name] for name in data["categories"]])
            created_count += 1

        self.stdout.write(self.style.SUCCESS(f"Created {created_count} new events."))

        if not User.objects.filter(is_superuser=True).exists():
            self.stdout.write(
                self.style.WARNING("No superuser exists yet — run `python manage.py createsuperuser` to access /admin/.")
            )

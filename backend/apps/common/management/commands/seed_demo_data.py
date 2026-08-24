"""
Seed reference and demo data (§18).

Idempotent: every row is created with get_or_create, so the command can be run
repeatedly — locally, in CI, or once against Supabase — without duplicating
reference data.

    python manage.py seed_demo_data
    python manage.py seed_demo_data --reference-only
"""

from datetime import timedelta

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from apps.common.enums import RegistrationStatus, SchoolLevelSlug, UserRole
from apps.events.models import Category, Event, EventCategory, SavedEvent, SchoolLevel
from apps.organizers.models import Institution
from apps.preferences.models import UserPreference, UserPreferenceCategory
from apps.registrations.models import EventRegistration
from apps.users.models import User

CATEGORIES = [
    ("Sports", "sports"),
    ("Math", "math"),
    ("English", "english"),
    ("Sciences", "sciences"),
    ("Chess", "chess"),
    ("Humanities", "humanities"),
    ("Languages", "languages"),
    ("Music", "music"),
]

SCHOOL_LEVELS = [
    ("Primary", SchoolLevelSlug.PRIMARY),
    ("Junior Secondary", SchoolLevelSlug.JUNIOR_SECONDARY),
    ("Senior Secondary", SchoolLevelSlug.SENIOR_SECONDARY),
    ("College", SchoolLevelSlug.COLLEGE),
]

DEMO_PASSWORD = "Funkies254!"


class Command(BaseCommand):
    help = "Seed categories, school levels and (optionally) demo accounts and events."

    def add_arguments(self, parser):
        parser.add_argument(
            "--reference-only",
            action="store_true",
            help="Seed only categories and school levels, skipping demo accounts and events.",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        categories = self._seed_categories()
        levels = self._seed_school_levels()
        self.stdout.write(
            self.style.SUCCESS(
                f"Reference data ready: {len(categories)} categories, {len(levels)} school levels."
            )
        )

        if options["reference_only"]:
            return

        institution = self._seed_institution()
        users = self._seed_users(institution, levels, categories)
        events = self._seed_events(institution, users["staff"], levels, categories)
        self._seed_student_activity(users["student"], events)

        self.stdout.write(self.style.SUCCESS(f"Demo institution: {institution.name}"))
        self.stdout.write(self.style.SUCCESS(f"Demo events: {len(events)}"))
        self.stdout.write("")
        self.stdout.write("Demo accounts (password for all: %s)" % DEMO_PASSWORD)
        for label, user in users.items():
            self.stdout.write(f"  {label:<12} {user.email:<34} role={user.role}")

    # ---------------------------------------------------------------- reference

    def _seed_categories(self):
        categories = {}
        for name, slug in CATEGORIES:
            category, _ = Category.objects.get_or_create(slug=slug, defaults={"name": name})
            categories[slug] = category
        return categories

    def _seed_school_levels(self):
        levels = {}
        for name, slug in SCHOOL_LEVELS:
            level, _ = SchoolLevel.objects.get_or_create(slug=slug, defaults={"name": name})
            levels[slug] = level
        return levels

    # --------------------------------------------------------------------- demo

    def _seed_institution(self):
        institution, _ = Institution.objects.get_or_create(
            slug="nairobi-high-school",
            defaults={
                "name": "Nairobi High School",
                "email": "events@nairobihigh.ac.ke",
                "phone": "+254700000001",
                "location": "Ngara, Nairobi",
                "website": "https://nairobihigh.ac.ke",
                "verified": True,
            },
        )
        return institution

    def _seed_users(self, institution, levels, categories):
        users = {
            "student": self._get_or_create_user(
                email="student@funkies254.test",
                name="Amina Wanjiru",
                role=UserRole.STUDENT,
                institution=institution,
            ),
            "staff": self._get_or_create_user(
                email="staff@funkies254.test",
                name="Brian Otieno",
                role=UserRole.INSTITUTION_STAFF,
                institution=institution,
            ),
            "admin": self._get_or_create_user(
                email="admin@funkies254.test",
                name="Faith Kamau",
                role=UserRole.ADMIN,
                is_staff=True,
            ),
            "super_admin": self._get_or_create_user(
                email="superadmin@funkies254.test",
                name="Joseph Mwangi",
                role=UserRole.SUPER_ADMIN,
                is_staff=True,
                is_superuser=True,
            ),
        }

        preference, _ = UserPreference.objects.get_or_create(
            user=users["student"],
            defaults={
                "school_level": levels[SchoolLevelSlug.SENIOR_SECONDARY],
                "email_notifications": True,
            },
        )
        if preference.school_level_id is None:
            preference.school_level = levels[SchoolLevelSlug.SENIOR_SECONDARY]
            preference.save(update_fields=["school_level"])

        for slug in ("math", "chess", "sports"):
            UserPreferenceCategory.objects.get_or_create(
                user_preference=preference, category=categories[slug]
            )

        if institution.created_by_id is None:
            institution.created_by = users["admin"]
            institution.save(update_fields=["created_by", "updated_at"])

        return users

    def _get_or_create_user(self, *, email, name, role, institution=None, **flags):
        user = User.objects.filter(email=email).first()
        if user is not None:
            return user
        user = User.objects.create_user(
            email=email,
            password=DEMO_PASSWORD,
            name=name,
            role=role,
            institution=institution,
            **flags,
        )
        UserPreference.objects.get_or_create(user=user)
        return user

    def _seed_events(self, institution, staff, levels, categories):
        now = timezone.now()
        blueprints = [
            {
                "slug": "nairobi-inter-school-math-olympiad",
                "title": "Nairobi Inter-School Math Olympiad",
                "description": (
                    "A one-day mathematics competition for senior secondary students "
                    "across Nairobi county. Teams of four compete in algebra, geometry "
                    "and problem-solving rounds."
                ),
                "start": now + timedelta(days=7),
                "hours": 6,
                "venue": "Nairobi High School Main Hall",
                "location": "Ngara, Nairobi",
                "level": SchoolLevelSlug.SENIOR_SECONDARY,
                "categories": ["math", "sciences"],
                "is_virtual": False,
            },
            {
                "slug": "county-chess-championship",
                "title": "County Chess Championship",
                "description": (
                    "Knockout chess tournament open to junior and senior secondary "
                    "students. Bring your own board if you have one."
                ),
                "start": now + timedelta(days=21),
                "hours": 8,
                "venue": "Nairobi High School Library",
                "location": "Ngara, Nairobi",
                "level": SchoolLevelSlug.JUNIOR_SECONDARY,
                "categories": ["chess"],
                "is_virtual": False,
            },
            {
                "slug": "virtual-debate-masterclass",
                "title": "Virtual Debate Masterclass",
                "description": (
                    "An online masterclass on argument construction and rebuttal "
                    "technique, led by national debate coaches."
                ),
                "start": now + timedelta(days=3),
                "hours": 2,
                "venue": None,
                "location": None,
                "level": SchoolLevelSlug.SENIOR_SECONDARY,
                "categories": ["english", "humanities"],
                "is_virtual": True,
            },
            {
                "slug": "regional-athletics-trials",
                "title": "Regional Athletics Trials",
                "description": (
                    "Track and field trials selecting the regional team for the "
                    "national championships."
                ),
                "start": now + timedelta(days=35),
                "hours": 10,
                "venue": "Nyayo National Stadium",
                "location": "Langata, Nairobi",
                "level": SchoolLevelSlug.SENIOR_SECONDARY,
                "categories": ["sports"],
                "is_virtual": False,
            },
        ]

        events = []
        for blueprint in blueprints:
            event, created = Event.objects.get_or_create(
                slug=blueprint["slug"],
                defaults={
                    "title": blueprint["title"],
                    "description": blueprint["description"],
                    "institution": institution,
                    "start_time": blueprint["start"],
                    "end_time": blueprint["start"] + timedelta(hours=blueprint["hours"]),
                    "venue": blueprint["venue"],
                    "location": blueprint["location"],
                    "school_level": levels[blueprint["level"]],
                    "is_virtual": blueprint["is_virtual"],
                    "registration_link": (
                        "https://meet.funkies254.test/debate" if blueprint["is_virtual"] else None
                    ),
                    "is_verified": True,
                    "verified_at": now,
                    "created_by": staff,
                },
            )
            if created:
                EventCategory.objects.bulk_create(
                    [
                        EventCategory(event=event, category=categories[slug])
                        for slug in blueprint["categories"]
                    ],
                    ignore_conflicts=True,
                )
            events.append(event)
        return events

    def _seed_student_activity(self, student, events):
        if not events:
            return
        SavedEvent.objects.get_or_create(user=student, event=events[0])
        EventRegistration.objects.get_or_create(
            user=student,
            event=events[0],
            defaults={"status": RegistrationStatus.REGISTERED},
        )

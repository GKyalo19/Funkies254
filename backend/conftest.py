"""Shared pytest fixtures."""

from datetime import timedelta

import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from apps.common.enums import SchoolLevelSlug, UserRole
from apps.events.models import Category, Event, EventCategory, SchoolLevel
from apps.organizers.models import Institution
from apps.preferences.models import UserPreference
from apps.users.models import User

PASSWORD = "TestPass!2026"


@pytest.fixture(autouse=True)
def _locmem_email(settings):
    settings.EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"


@pytest.fixture
def api():
    return APIClient()


@pytest.fixture
def categories(db):
    return {
        slug: Category.objects.create(name=name, slug=slug)
        for name, slug in (("Sports", "sports"), ("Math", "math"), ("Chess", "chess"))
    }


@pytest.fixture
def school_levels(db):
    return {
        slug: SchoolLevel.objects.create(name=name, slug=slug)
        for name, slug in (
            ("Senior Secondary", SchoolLevelSlug.SENIOR_SECONDARY.value),
            ("College", SchoolLevelSlug.COLLEGE.value),
        )
    }


@pytest.fixture
def institution(db):
    return Institution.objects.create(
        name="Nairobi High School", slug="nairobi-high-school", location="Ngara, Nairobi", verified=True
    )


@pytest.fixture
def other_institution(db):
    return Institution.objects.create(name="Mombasa Academy", slug="mombasa-academy", verified=True)


def _make_user(email, role, institution=None, **flags):
    flags.setdefault("email_verified", True)
    user = User.objects.create_user(
        email=email, password=PASSWORD, name=email.split("@")[0].title(), role=role,
        institution=institution, **flags
    )
    UserPreference.objects.create(user=user)
    return user


@pytest.fixture
def student(db, institution):
    return _make_user("student@example.com", UserRole.STUDENT, institution)


@pytest.fixture
def other_student(db):
    return _make_user("student2@example.com", UserRole.STUDENT)


@pytest.fixture
def staff(db, institution):
    return _make_user("staff@example.com", UserRole.INSTITUTION_STAFF, institution)


@pytest.fixture
def other_staff(db, other_institution):
    return _make_user("staff2@example.com", UserRole.INSTITUTION_STAFF, other_institution)


@pytest.fixture
def admin_user(db):
    return _make_user("admin@example.com", UserRole.ADMIN, is_staff=True)


@pytest.fixture
def super_admin(db):
    return _make_user("super@example.com", UserRole.SUPER_ADMIN, is_staff=True, is_superuser=True)


@pytest.fixture
def login(api):
    """Authenticate a user through the real login endpoint so cookies are set."""

    def _login(user, password=PASSWORD):
        response = api.post(
            "/api/auth/login/", {"email": user.email, "password": password}, format="json"
        )
        assert response.status_code == 200, response.data
        return response

    return _login


@pytest.fixture
def event(db, institution, staff, school_levels, categories):
    instance = Event.objects.create(
        title="Nairobi Math Olympiad",
        description="County mathematics competition.",
        institution=institution,
        start_time=timezone.now() + timedelta(days=7),
        end_time=timezone.now() + timedelta(days=7, hours=6),
        venue="Main Hall",
        location="Ngara, Nairobi",
        school_level=school_levels[SchoolLevelSlug.SENIOR_SECONDARY.value],
        is_verified=True,
        created_by=staff,
    )
    EventCategory.objects.create(event=instance, category=categories["math"])
    return instance


@pytest.fixture
def event_payload(institution, school_levels, categories):
    start = timezone.now() + timedelta(days=30)
    return {
        "title": "County Chess Championship",
        "description": "Knockout chess tournament for secondary students.",
        "institution_id": str(institution.id),
        "start_time": start.isoformat(),
        "end_time": (start + timedelta(hours=8)).isoformat(),
        "venue": "School Library",
        "location": "Ngara, Nairobi",
        "school_level_id": str(school_levels[SchoolLevelSlug.SENIOR_SECONDARY.value].id),
        "category_ids": [str(categories["chess"].id)],
    }

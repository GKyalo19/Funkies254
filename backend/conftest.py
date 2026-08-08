"""Shared pytest fixtures available to every test in the backend."""
import pytest
from rest_framework.test import APIClient


@pytest.fixture
def api_client():
    """
    A DRF APIClient. Because our auth tokens live in cookies (not headers),
    this plain client is enough — Django's test client keeps a cookie jar
    across requests automatically, exactly like a real browser session.
    """
    return APIClient()


@pytest.fixture
def create_user(db):
    from apps.users.models import User

    def _create_user(email="student@example.com", password="StrongPass123", **kwargs):
        return User.objects.create_user(email=email, password=password, **kwargs)

    return _create_user


@pytest.fixture
def create_staff_user(create_user):
    def _create_staff_user(email="admin@example.com", password="StrongPass123", **kwargs):
        kwargs["is_staff"] = True
        return create_user(email=email, password=password, **kwargs)

    return _create_staff_user


@pytest.fixture
def logged_in_client(api_client, create_user):
    """Returns (client, user) already authenticated via the real /api/auth/login/ endpoint."""

    def _logged_in_client(**user_kwargs):
        password = user_kwargs.pop("password", "StrongPass123")
        user = create_user(password=password, **user_kwargs)
        response = api_client.post("/api/auth/login/", {"email": user.email, "password": password})
        assert response.status_code == 200
        return api_client, user

    return _logged_in_client


@pytest.fixture
def organizer(db):
    from apps.organizers.models import Organizer

    return Organizer.objects.create(name="Brookside Kenya", years_hosting=10)


@pytest.fixture
def category(db):
    from apps.events.models import Category

    return Category.objects.create(name="Math")


@pytest.fixture
def make_event(db, organizer):
    from django.utils import timezone

    from apps.events.models import Event

    def _make_event(**kwargs):
        defaults = {
            "title": "64th Annual Math Olympiad",
            "organizer": organizer,
            "description": "A fun math competition.",
            "venue_name": "Mang'u High School",
            "location": "Nairobi",
            "start_datetime": timezone.now() + timezone.timedelta(days=7),
            "status": "published",
        }
        defaults.update(kwargs)
        return Event.objects.create(**defaults)

    return _make_event

"""Pre-launch event behaviour: external registration clicks, search, popularity."""

from datetime import timedelta

import pytest
from django.utils import timezone

from apps.common.enums import InteractionKind
from apps.events.models import Event, EventInteraction, SearchQuery
from apps.events.services import compute_popularity

pytestmark = pytest.mark.django_db

LIST_URL = "/api/events/"


def test_search_includes_past_events_and_is_logged(api, event, staff):
    Event.objects.create(
        title="Past Olympiad",
        description="Already finished.",
        start_time=timezone.now() - timedelta(days=5),
        end_time=timezone.now() - timedelta(days=4),
        created_by=staff,
        is_verified=True,
    )

    response = api.get(f"{LIST_URL}?search=olympiad")

    assert response.status_code == 200
    assert response.data["count"] == 2
    assert response.data["results"][0]["is_past"] is False
    assert response.data["results"][1]["is_past"] is True
    assert SearchQuery.objects.filter(query="olympiad", results_count=2).exists()


def test_click_out_is_public(api, event):
    response = api.post(f"{LIST_URL}{event.id}/click-out/", {}, format="json")

    assert response.status_code == 200
    assert EventInteraction.objects.filter(event=event, kind=InteractionKind.CLICK_OUT).count() == 1


def test_detail_view_is_counted_once_per_hour(api, event):
    assert api.get(f"{LIST_URL}{event.slug}/").status_code == 200
    assert api.get(f"{LIST_URL}{event.slug}/").status_code == 200

    assert EventInteraction.objects.filter(event=event, kind=InteractionKind.VIEW).count() == 1


def test_popularity_uses_saves_clicks_views_and_mentions(db, event, student):
    from apps.events.models import SavedEvent

    SavedEvent.objects.create(user=student, event=event)
    EventInteraction.objects.create(event=event, kind=InteractionKind.CLICK_OUT)
    EventInteraction.objects.create(event=event, kind=InteractionKind.VIEW)
    event.external_mentions = 2
    event.save(update_fields=["external_mentions"])

    compute_popularity()
    event.refresh_from_db()

    assert event.popularity_score == 3 + 2 + 1 + 10


def test_sections_list_nests_categories(api):
    from apps.events.taxonomy import seed_taxonomy
    from django.apps import apps

    seed_taxonomy(apps)
    response = api.get("/api/sections/")

    assert response.status_code == 200
    slugs = [row["slug"] for row in response.data]
    assert slugs[:3] == ["college-events", "high-school-events", "college-app-resources"]
    college = next(row for row in response.data if row["slug"] == "college-events")
    assert any(category["slug"] == "health-medicine" for category in college["categories"])

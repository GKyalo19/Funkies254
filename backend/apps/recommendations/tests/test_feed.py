"""Recommendation tests (§15: preference matching, anonymous fallback,
deterministic ranking)."""

from datetime import timedelta

import pytest
from django.utils import timezone

from apps.events.models import Event, EventCategory
from apps.preferences.models import UserPreference, UserPreferenceCategory
from apps.recommendations.services import recommend_events

pytestmark = pytest.mark.django_db

URL = "/api/recommendations/feed/"


@pytest.fixture
def feed_events(db, staff, institution, school_levels, categories):
    """Three upcoming events with different matching characteristics."""
    now = timezone.now()

    def make(title, days, category=None, level=None, location=None, institution_obj=None):
        event = Event.objects.create(
            title=title,
            description=f"{title} description.",
            institution=institution_obj,
            start_time=now + timedelta(days=days),
            end_time=now + timedelta(days=days, hours=4),
            location=location,
            school_level=level,
            is_verified=True,
            created_by=staff,
        )
        if category:
            EventCategory.objects.create(event=event, category=category)
        return event

    return {
        "matching": make(
            "Chess Masters",
            days=40,
            category=categories["chess"],
            level=school_levels["senior-secondary"],
            location="Ngara, Nairobi",
            institution_obj=institution,
        ),
        "soon": make("Random Meetup", days=1),
        "unrelated": make("Sports Gala", days=45, category=categories["sports"]),
    }


def test_anonymous_feed_returns_soonest_upcoming_events(api, feed_events):
    response = api.get(URL)

    assert response.status_code == 200
    assert response.data["personalised"] is False
    titles = [row["event"]["title"] for row in response.data["results"]]
    assert titles[0] == "Random Meetup"


def test_anonymous_feed_excludes_unverified_and_past_events(api, staff, feed_events):
    Event.objects.create(
        title="Hidden Draft",
        description="Unverified.",
        start_time=timezone.now() + timedelta(days=2),
        end_time=timezone.now() + timedelta(days=2, hours=1),
        created_by=staff,
    )
    Event.objects.create(
        title="Old Event",
        description="Finished.",
        start_time=timezone.now() - timedelta(days=4),
        end_time=timezone.now() - timedelta(days=3),
        created_by=staff,
        is_verified=True,
    )

    titles = [row["event"]["title"] for row in api.get(URL).data["results"]]

    assert "Hidden Draft" not in titles
    assert "Old Event" not in titles


def test_preference_match_outranks_a_sooner_unrelated_event(
    api, student, feed_events, categories, school_levels, login
):
    preference = UserPreference.objects.get(user=student)
    preference.school_level = school_levels["senior-secondary"]
    preference.save()
    UserPreferenceCategory.objects.create(
        user_preference=preference, category=categories["chess"]
    )

    login(student)
    response = api.get(URL)

    assert response.data["personalised"] is True
    results = response.data["results"]
    assert results[0]["event"]["title"] == "Chess Masters"
    assert results[0]["score"] > results[1]["score"]


def test_reasons_explain_every_matching_rule(
    api, student, feed_events, categories, school_levels, login
):
    preference = UserPreference.objects.get(user=student)
    preference.school_level = school_levels["senior-secondary"]
    preference.save()
    UserPreferenceCategory.objects.create(
        user_preference=preference, category=categories["chess"]
    )

    login(student)
    top = api.get(URL).data["results"][0]

    rules = {reason["rule"] for reason in top["reasons"]}
    assert "category_overlap" in rules
    assert "school_level_match" in rules
    assert "location_match" in rules
    assert "institution_match" in rules


def test_ranking_is_deterministic(db, student, feed_events, categories):
    preference = UserPreference.objects.get(user=student)
    UserPreferenceCategory.objects.create(
        user_preference=preference, category=categories["chess"]
    )

    first = [item.event.id for item in recommend_events(user=student)]
    second = [item.event.id for item in recommend_events(user=student)]

    assert first == second


def test_limit_is_respected(api, feed_events):
    response = api.get(f"{URL}?limit=2")

    assert len(response.data["results"]) == 2


def test_user_without_preferences_gets_fallback_ordering(api, other_student, feed_events, login):
    login(other_student)
    response = api.get(URL)

    titles = [row["event"]["title"] for row in response.data["results"]]
    assert titles[0] == "Random Meetup"

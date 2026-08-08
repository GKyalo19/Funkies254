import pytest
from django.utils import timezone

from apps.recommendations.services import rank_events_for_user

pytestmark = pytest.mark.django_db


class TestRankEventsForUser:
    def test_anonymous_user_sees_featured_events_first(self, make_event):
        make_event(title="Regular Event", is_featured=False, start_datetime=timezone.now() + timezone.timedelta(days=2))
        featured = make_event(title="Featured Event", is_featured=True, start_datetime=timezone.now() + timezone.timedelta(days=20))

        ranked = rank_events_for_user(None)
        assert ranked[0].id == featured.id

    def test_matching_category_boosts_event_above_unrelated_one(self, make_event, category, create_user):
        from apps.preferences.models import UserPreference

        user = create_user(email="student@example.com")
        preference = UserPreference.objects.create(user=user)
        preference.categories.add(category)

        matching = make_event(title="Math Olympiad", start_datetime=timezone.now() + timezone.timedelta(days=10))
        matching.categories.add(category)
        unrelated = make_event(title="Unrelated Event", start_datetime=timezone.now() + timezone.timedelta(days=1))

        ranked = rank_events_for_user(user)
        assert ranked.index(matching) < ranked.index(unrelated)

    def test_followed_organizer_events_rank_higher(self, make_event, create_user):
        from apps.organizers.models import Follow, Organizer

        user = create_user(email="student@example.com")
        followed_organizer = Organizer.objects.create(name="Followed Org")
        Follow.objects.create(user=user, organizer=followed_organizer)

        followed_event = make_event(title="From Followed Org", organizer=followed_organizer, start_datetime=timezone.now() + timezone.timedelta(days=15))
        other_event = make_event(title="From Other Org", start_datetime=timezone.now() + timezone.timedelta(days=1))

        ranked = rank_events_for_user(user)
        assert ranked.index(followed_event) < ranked.index(other_event)

    def test_past_events_are_excluded(self, make_event):
        make_event(title="Past Event", start_datetime=timezone.now() - timezone.timedelta(days=1))
        upcoming = make_event(title="Upcoming Event", start_datetime=timezone.now() + timezone.timedelta(days=1))

        ranked = rank_events_for_user(None)
        assert ranked == [upcoming]


class TestFeedEndpoint:
    def test_feed_endpoint_returns_upcoming_events(self, api_client, make_event):
        make_event(title="Upcoming Event")
        response = api_client.get("/api/recommendations/feed/")
        assert response.status_code == 200
        assert response.data["count"] == 1

    def test_feed_respects_limit_param(self, api_client, make_event):
        from django.utils import timezone as tz

        for i in range(5):
            make_event(title=f"Event {i}", start_datetime=tz.now() + tz.timedelta(days=i + 1))

        response = api_client.get("/api/recommendations/feed/?limit=2")
        assert response.data["count"] == 2

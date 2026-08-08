import pytest

pytestmark = pytest.mark.django_db


class TestEventList:
    def test_anonymous_user_can_list_published_events(self, api_client, make_event):
        make_event(title="Public Event")
        response = api_client.get("/api/events/")
        assert response.status_code == 200
        assert response.data["count"] == 1

    def test_draft_events_hidden_from_anonymous_users(self, api_client, make_event):
        make_event(title="Draft Event", status="draft")
        response = api_client.get("/api/events/")
        assert response.data["count"] == 0

    def test_staff_can_see_draft_events(self, api_client, make_event, create_staff_user):
        make_event(title="Draft Event", status="draft")
        create_staff_user(email="admin@example.com", password="StrongPass123")
        api_client.post("/api/auth/login/", {"email": "admin@example.com", "password": "StrongPass123"})
        response = api_client.get("/api/events/")
        assert response.data["count"] == 1

    def test_filter_by_category(self, api_client, make_event, category):
        matching = make_event(title="Math Olympiad")
        matching.categories.add(category)
        make_event(title="Unrelated Event")

        response = api_client.get(f"/api/events/?category={category.slug}")
        assert response.data["count"] == 1
        assert response.data["results"][0]["title"] == "Math Olympiad"

    def test_filter_free_events(self, api_client, make_event):
        make_event(title="Free Event", registration_fee=0)
        make_event(title="Paid Event", registration_fee=500)

        response = api_client.get("/api/events/?fee=free")
        assert response.data["count"] == 1
        assert response.data["results"][0]["title"] == "Free Event"

    def test_filter_by_location(self, api_client, make_event):
        make_event(title="Nairobi Event", location="Nairobi")
        make_event(title="Thika Event", location="Thika")

        response = api_client.get("/api/events/?location=Nairobi")
        assert response.data["count"] == 1


class TestEventDetail:
    def test_retrieve_event_by_slug(self, api_client, make_event):
        event = make_event(title="64th Annual Math Olympiad")
        response = api_client.get(f"/api/events/{event.slug}/")
        assert response.status_code == 200
        assert response.data["title"] == event.title

    def test_similar_events_shares_category(self, api_client, make_event, category):
        event = make_event(title="Main Event")
        event.categories.add(category)
        similar = make_event(title="Similar Event")
        similar.categories.add(category)
        make_event(title="Unrelated Event")

        response = api_client.get(f"/api/events/{event.slug}/similar/")
        assert response.status_code == 200
        titles = [item["title"] for item in response.data]
        assert "Similar Event" in titles
        assert "Unrelated Event" not in titles
        assert "Main Event" not in titles


class TestEventWritePermissions:
    def test_anonymous_user_cannot_create_event(self, api_client, organizer):
        response = api_client.post("/api/events/", {"title": "New Event", "organizer": organizer.id})
        assert response.status_code in (401, 403)

    def test_regular_student_cannot_create_event(self, api_client, organizer, create_user):
        create_user(email="student@example.com", password="StrongPass123")
        api_client.post("/api/auth/login/", {"email": "student@example.com", "password": "StrongPass123"})
        response = api_client.post("/api/events/", {"title": "New Event", "organizer": organizer.id})
        assert response.status_code == 403

    def test_staff_can_create_event(self, api_client, organizer, create_staff_user):
        create_staff_user(email="admin@example.com", password="StrongPass123")
        api_client.post("/api/auth/login/", {"email": "admin@example.com", "password": "StrongPass123"})
        response = api_client.post(
            "/api/events/",
            {
                "title": "New Event",
                "organizer": organizer.id,
                "description": "Details",
                "venue_name": "Venue",
                "location": "Nairobi",
                "start_datetime": "2027-01-01T10:00:00Z",
            },
        )
        assert response.status_code == 201

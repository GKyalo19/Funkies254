import pytest

pytestmark = pytest.mark.django_db


class TestRegistrationFlow:
    def test_requires_authentication(self, api_client, make_event):
        event = make_event()
        response = api_client.post("/api/registrations/", {"event_slug": event.slug})
        assert response.status_code == 401

    def test_student_can_register_for_event(self, logged_in_client, make_event):
        client, _user = logged_in_client()
        event = make_event()

        response = client.post("/api/registrations/", {"event_slug": event.slug})
        assert response.status_code == 201
        assert response.data["event"]["title"] == event.title

        my_registrations = client.get("/api/registrations/")
        assert my_registrations.data["count"] == 1

    def test_cannot_register_twice_creates_single_row(self, logged_in_client, make_event):
        from apps.registrations.models import Registration

        client, _user = logged_in_client()
        event = make_event()

        client.post("/api/registrations/", {"event_slug": event.slug})
        client.post("/api/registrations/", {"event_slug": event.slug})

        assert Registration.objects.count() == 1

    def test_cannot_register_for_full_event(self, logged_in_client, make_event, create_user):
        client, _user = logged_in_client(email="a@example.com")
        event = make_event(capacity=1)

        first = client.post("/api/registrations/", {"event_slug": event.slug})
        assert first.status_code == 201

        client2, _user2 = logged_in_client(email="b@example.com")
        second = client2.post("/api/registrations/", {"event_slug": event.slug})
        assert second.status_code == 400

    def test_cancel_registration_marks_cancelled(self, logged_in_client, make_event):
        from apps.registrations.models import Registration

        client, _user = logged_in_client()
        event = make_event()
        create_response = client.post("/api/registrations/", {"event_slug": event.slug})
        registration_id = create_response.data["id"]

        delete_response = client.delete(f"/api/registrations/{registration_id}/")
        assert delete_response.status_code == 204
        assert Registration.objects.get(pk=registration_id).status == "cancelled"

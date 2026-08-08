import pytest

pytestmark = pytest.mark.django_db


class TestOrganizerFollow:
    def test_anonymous_user_can_view_organizers(self, api_client, organizer):
        response = api_client.get("/api/organizers/")
        assert response.status_code == 200
        assert response.data["count"] == 1

    def test_follow_requires_authentication(self, api_client, organizer):
        response = api_client.post(f"/api/organizers/{organizer.slug}/follow/")
        assert response.status_code == 401

    def test_student_can_follow_and_unfollow(self, logged_in_client, organizer):
        client, _user = logged_in_client()

        follow_response = client.post(f"/api/organizers/{organizer.slug}/follow/")
        assert follow_response.status_code == 200

        detail_response = client.get(f"/api/organizers/{organizer.slug}/")
        assert detail_response.data["is_following"] is True
        assert detail_response.data["followers_count"] == 1

        unfollow_response = client.delete(f"/api/organizers/{organizer.slug}/follow/")
        assert unfollow_response.status_code == 200

        detail_after = client.get(f"/api/organizers/{organizer.slug}/")
        assert detail_after.data["is_following"] is False

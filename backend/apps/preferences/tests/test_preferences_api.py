import pytest

pytestmark = pytest.mark.django_db


class TestPreferencesEndpoint:
    def test_requires_authentication(self, api_client):
        response = api_client.get("/api/preferences/me/")
        assert response.status_code == 401

    def test_get_creates_default_preference(self, logged_in_client):
        client, _user = logged_in_client()
        response = client.get("/api/preferences/me/")
        assert response.status_code == 200
        assert response.data["max_days_ahead"] == 30
        assert response.data["categories"] == []

    def test_update_preference_categories_and_locations(self, logged_in_client, category):
        client, _user = logged_in_client()
        response = client.patch(
            "/api/preferences/me/",
            {"categories": [category.id], "preferred_locations": ["Nairobi"], "education_levels": ["high_school"]},
            format="json",
        )
        assert response.status_code == 200
        assert response.data["categories"] == [category.id]
        assert response.data["preferred_locations"] == ["Nairobi"]

    def test_invalid_education_level_rejected(self, logged_in_client):
        client, _user = logged_in_client()
        response = client.patch("/api/preferences/me/", {"education_levels": ["not_a_real_level"]}, format="json")
        assert response.status_code == 400

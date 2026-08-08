import pytest
from django.conf import settings

pytestmark = pytest.mark.django_db


class TestRegister:
    def test_register_creates_user_and_sets_cookies(self, api_client):
        response = api_client.post(
            "/api/auth/register/",
            {
                "email": "new.student@example.com",
                "password": "StrongPass123",
                "confirm_password": "StrongPass123",
                "institution": "Mang'u High School",
                "education_level": "high_school",
            },
        )
        assert response.status_code == 201
        assert response.data["user"]["email"] == "new.student@example.com"
        assert settings.ACCESS_TOKEN_COOKIE in response.cookies
        assert settings.REFRESH_TOKEN_COOKIE in response.cookies

    def test_register_rejects_mismatched_passwords(self, api_client):
        response = api_client.post(
            "/api/auth/register/",
            {"email": "x@example.com", "password": "StrongPass123", "confirm_password": "Different123"},
        )
        assert response.status_code == 400

    def test_register_rejects_duplicate_email(self, api_client, create_user):
        create_user(email="taken@example.com")
        response = api_client.post(
            "/api/auth/register/",
            {"email": "taken@example.com", "password": "StrongPass123", "confirm_password": "StrongPass123"},
        )
        assert response.status_code == 400


class TestLogin:
    def test_login_succeeds_with_correct_credentials(self, api_client, create_user):
        create_user(email="student@example.com", password="StrongPass123")
        response = api_client.post("/api/auth/login/", {"email": "student@example.com", "password": "StrongPass123"})
        assert response.status_code == 200
        assert settings.ACCESS_TOKEN_COOKIE in response.cookies

    def test_login_fails_with_wrong_password(self, api_client, create_user):
        create_user(email="student@example.com", password="StrongPass123")
        response = api_client.post("/api/auth/login/", {"email": "student@example.com", "password": "WrongPass"})
        assert response.status_code == 400


class TestMeEndpoint:
    def test_me_requires_authentication(self, api_client):
        response = api_client.get("/api/users/me/")
        assert response.status_code == 401

    def test_me_returns_profile_when_logged_in(self, logged_in_client):
        client, user = logged_in_client(email="student@example.com")
        response = client.get("/api/users/me/")
        assert response.status_code == 200
        assert response.data["email"] == user.email

    def test_logout_clears_cookies_and_blocks_me(self, logged_in_client):
        client, _user = logged_in_client()
        logout_response = client.post("/api/auth/logout/")
        assert logout_response.status_code == 200
        # The test client's cookie jar retains the now-empty/deleted cookie value.
        me_response = client.get("/api/users/me/")
        assert me_response.status_code == 401


class TestPasswordReset:
    def test_request_always_returns_200(self, api_client, create_user):
        create_user(email="student@example.com")
        response = api_client.post("/api/auth/password-reset/request/", {"email": "student@example.com"})
        assert response.status_code == 200

        response_unknown = api_client.post("/api/auth/password-reset/request/", {"email": "nobody@example.com"})
        assert response_unknown.status_code == 200

    def test_confirm_with_valid_token_changes_password(self, api_client, create_user):
        from django.utils.encoding import force_bytes
        from django.utils.http import urlsafe_base64_encode

        from apps.users.tokens import password_reset_token

        user = create_user(email="student@example.com", password="OldPass123")
        uid = urlsafe_base64_encode(force_bytes(user.pk))
        token = password_reset_token.make_token(user)

        response = api_client.post(
            "/api/auth/password-reset/confirm/", {"uid": uid, "token": token, "new_password": "NewPass456"}
        )
        assert response.status_code == 200

        login_response = api_client.post("/api/auth/login/", {"email": "student@example.com", "password": "NewPass456"})
        assert login_response.status_code == 200

    def test_confirm_with_invalid_token_fails(self, api_client, create_user):
        from django.utils.encoding import force_bytes
        from django.utils.http import urlsafe_base64_encode

        user = create_user(email="student@example.com")
        uid = urlsafe_base64_encode(force_bytes(user.pk))

        response = api_client.post(
            "/api/auth/password-reset/confirm/", {"uid": uid, "token": "bad-token", "new_password": "NewPass456"}
        )
        assert response.status_code == 400

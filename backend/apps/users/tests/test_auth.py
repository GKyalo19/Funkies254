"""Authentication tests (§15: register, login, duplicate email, invalid password,
refresh, logout, inactive user)."""

import pytest
from django.conf import settings

from apps.preferences.models import UserPreference
from apps.users.models import User

pytestmark = pytest.mark.django_db

REGISTER_URL = "/api/auth/register/"
LOGIN_URL = "/api/auth/login/"
REFRESH_URL = "/api/auth/token/refresh/"
LOGOUT_URL = "/api/auth/logout/"
ME_URL = "/api/users/me/"

VALID_PAYLOAD = {
    "email": "New.Student@Example.com",
    "name": "New Student",
    "password": "StrongPass!2026",
    "password_confirm": "StrongPass!2026",
}


def test_register_creates_user_preference_and_cookies(api):
    response = api.post(REGISTER_URL, VALID_PAYLOAD, format="json")

    assert response.status_code == 201, response.data
    user = User.objects.get(email="new.student@example.com")
    assert user.role == "student"
    assert UserPreference.objects.filter(user=user).exists()
    assert settings.JWT_ACCESS_COOKIE_NAME in response.cookies
    assert settings.JWT_REFRESH_COOKIE_NAME in response.cookies
    assert response.cookies[settings.JWT_ACCESS_COOKIE_NAME]["httponly"]
    assert "password" not in response.data["user"]


def test_register_normalises_email_to_lowercase(api):
    api.post(REGISTER_URL, VALID_PAYLOAD, format="json")
    assert User.objects.filter(email="new.student@example.com").exists()


def test_register_rejects_duplicate_email(api, student):
    payload = {**VALID_PAYLOAD, "email": student.email.upper()}
    response = api.post(REGISTER_URL, payload, format="json")

    assert response.status_code == 400
    assert "email" in response.data["errors"]


def test_register_rejects_mismatched_passwords(api):
    payload = {**VALID_PAYLOAD, "password_confirm": "SomethingElse!2026"}
    response = api.post(REGISTER_URL, payload, format="json")

    assert response.status_code == 400
    assert "password_confirm" in response.data["errors"]


def test_register_rejects_weak_password(api):
    payload = {**VALID_PAYLOAD, "password": "password", "password_confirm": "password"}
    response = api.post(REGISTER_URL, payload, format="json")

    assert response.status_code == 400
    assert "password" in response.data["errors"]


def test_register_cannot_self_assign_elevated_role(api):
    response = api.post(REGISTER_URL, {**VALID_PAYLOAD, "role": "admin"}, format="json")

    assert response.status_code == 201
    assert User.objects.get(email="new.student@example.com").role == "student"


def test_login_succeeds_and_sets_cookies(api, student, login):
    response = login(student)

    assert response.data["user"]["email"] == student.email
    assert settings.JWT_ACCESS_COOKIE_NAME in response.cookies


def test_login_is_case_insensitive(api, student):
    response = api.post(
        LOGIN_URL, {"email": student.email.upper(), "password": "TestPass!2026"}, format="json"
    )
    assert response.status_code == 200


def test_login_rejects_invalid_password(api, student):
    response = api.post(LOGIN_URL, {"email": student.email, "password": "wrong"}, format="json")

    assert response.status_code == 401
    assert response.data["detail"] == "Invalid email or password."


def test_login_rejects_unknown_email(api):
    response = api.post(
        LOGIN_URL, {"email": "nobody@example.com", "password": "whatever"}, format="json"
    )
    assert response.status_code == 401


def test_inactive_user_cannot_log_in(api, student):
    student.is_active = False
    student.save(update_fields=["is_active"])

    response = api.post(LOGIN_URL, {"email": student.email, "password": "TestPass!2026"}, format="json")

    assert response.status_code == 401
    assert "suspended" in response.data["detail"].lower()


def test_cookie_authenticates_subsequent_request(api, student, login):
    login(student)
    response = api.get(ME_URL)

    assert response.status_code == 200
    assert response.data["email"] == student.email


def test_unauthenticated_request_is_rejected(api):
    assert api.get(ME_URL).status_code == 401


def test_refresh_rotates_cookies(api, student, login):
    login(student)
    response = api.post(REFRESH_URL, format="json")

    assert response.status_code == 200
    assert settings.JWT_ACCESS_COOKIE_NAME in response.cookies
    assert api.get(ME_URL).status_code == 200


def test_refresh_without_token_is_unauthorised(api):
    assert api.post(REFRESH_URL, format="json").status_code == 401


def test_refresh_rejects_blacklisted_token(api, student, login):
    login(student)
    api.post(LOGOUT_URL, format="json")
    api.cookies[settings.JWT_REFRESH_COOKIE_NAME] = "not-a-real-token"

    assert api.post(REFRESH_URL, format="json").status_code == 401


def test_logout_clears_cookies(api, student, login):
    login(student)
    response = api.post(LOGOUT_URL, format="json")

    assert response.status_code == 200
    assert response.cookies[settings.JWT_ACCESS_COOKIE_NAME].value == ""
    assert response.cookies[settings.JWT_REFRESH_COOKIE_NAME].value == ""


def test_suspended_user_token_stops_working(api, student, login):
    login(student)
    student.is_active = False
    student.save(update_fields=["is_active"])

    assert api.get(ME_URL).status_code == 401


def test_me_patch_updates_own_profile(api, student, login):
    login(student)
    response = api.patch(ME_URL, {"name": "Updated Name"}, format="json")

    assert response.status_code == 200
    student.refresh_from_db()
    assert student.name == "Updated Name"


def test_me_patch_cannot_change_role_or_email(api, student, login):
    login(student)
    api.patch(ME_URL, {"role": "admin", "email": "hacker@example.com"}, format="json")

    student.refresh_from_db()
    assert student.role == "student"
    assert student.email == "student@example.com"


def test_cookie_write_is_rejected_without_csrf_token_when_enforced(settings, student):
    from rest_framework.test import APIClient

    settings.JWT_COOKIE_CSRF_ENFORCED = True
    client = APIClient(enforce_csrf_checks=True)
    client.post(
        LOGIN_URL, {"email": student.email, "password": "TestPass!2026"}, format="json"
    )

    response = client.patch(ME_URL, {"name": "No CSRF"}, format="json")

    assert response.status_code == 403
    assert "CSRF" in response.data["detail"]


def test_cookie_write_succeeds_with_csrf_token_when_enforced(settings, student):
    from rest_framework.test import APIClient

    settings.JWT_COOKIE_CSRF_ENFORCED = True
    client = APIClient(enforce_csrf_checks=True)
    login_response = client.post(
        LOGIN_URL, {"email": student.email, "password": "TestPass!2026"}, format="json"
    )

    response = client.patch(
        ME_URL,
        {"name": "With CSRF"},
        format="json",
        HTTP_X_CSRFTOKEN=login_response.data["csrf_token"],
    )

    assert response.status_code == 200, response.data
    student.refresh_from_db()
    assert student.name == "With CSRF"


def test_header_authentication_is_exempt_from_csrf(settings, student):
    """Browsers never attach an Authorization header on their own."""
    from rest_framework.test import APIClient
    from rest_framework_simplejwt.tokens import RefreshToken

    settings.JWT_COOKIE_CSRF_ENFORCED = True
    access = RefreshToken.for_user(student).access_token
    client = APIClient(enforce_csrf_checks=True)

    response = client.patch(
        ME_URL, {"name": "Header Auth"}, format="json", HTTP_AUTHORIZATION=f"Bearer {access}"
    )

    assert response.status_code == 200, response.data


def test_staff_cannot_move_themselves_between_institutions(api, staff, other_institution, login):
    login(staff)
    response = api.patch(
        ME_URL, {"institution_id": str(other_institution.id)}, format="json"
    )

    assert response.status_code == 400
    staff.refresh_from_db()
    assert staff.institution_id != other_institution.id

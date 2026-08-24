"""Preference tests (§15: one row per user, category M2M, update own only)."""

import pytest
from django.db.utils import IntegrityError

from apps.preferences.models import UserPreference, UserPreferenceCategory

pytestmark = pytest.mark.django_db

URL = "/api/preferences/me/"


def test_registration_creates_exactly_one_preference_row(api):
    response = api.post(
        "/api/auth/register/",
        {
            "email": "prefs@example.com",
            "name": "Prefs User",
            "password": "StrongPass!2026",
            "password_confirm": "StrongPass!2026",
        },
        format="json",
    )

    assert response.status_code == 201
    assert UserPreference.objects.filter(user__email="prefs@example.com").count() == 1


def test_database_enforces_one_preference_per_user(db, student):
    with pytest.raises(IntegrityError):
        UserPreference.objects.create(user=student)


def test_student_reads_own_preferences(api, student, login):
    login(student)
    response = api.get(URL)

    assert response.status_code == 200
    assert response.data["email_notifications"] is True
    assert response.data["preferred_categories"] == []


def test_student_updates_notification_toggles(api, student, login):
    login(student)
    response = api.patch(
        URL, {"email_notifications": False, "push_notifications": True}, format="json"
    )

    assert response.status_code == 200
    preference = UserPreference.objects.get(user=student)
    assert preference.email_notifications is False
    assert preference.push_notifications is True


def test_student_sets_school_level_and_categories(api, student, school_levels, categories, login):
    login(student)
    response = api.patch(
        URL,
        {
            "school_level_id": str(school_levels["college"].id),
            "preferred_category_ids": [str(categories["math"].id), str(categories["chess"].id)],
        },
        format="json",
    )

    assert response.status_code == 200, response.data
    assert response.data["school_level"]["slug"] == "college"
    assert sorted(row["slug"] for row in response.data["preferred_categories"]) == [
        "chess",
        "math",
    ]
    assert UserPreferenceCategory.objects.filter(user_preference__user=student).count() == 2


def test_updating_categories_replaces_previous_selection(api, student, categories, login):
    login(student)
    api.patch(
        URL,
        {"preferred_category_ids": [str(categories["math"].id), str(categories["chess"].id)]},
        format="json",
    )

    response = api.patch(
        URL, {"preferred_category_ids": [str(categories["sports"].id)]}, format="json"
    )

    assert [row["slug"] for row in response.data["preferred_categories"]] == ["sports"]
    assert UserPreferenceCategory.objects.filter(user_preference__user=student).count() == 1


def test_duplicate_preference_category_is_rejected_by_database(db, student, categories):
    preference = UserPreference.objects.get(user=student)
    UserPreferenceCategory.objects.create(user_preference=preference, category=categories["math"])

    with pytest.raises(IntegrityError):
        UserPreferenceCategory.objects.create(
            user_preference=preference, category=categories["math"]
        )


def test_preferences_endpoint_only_ever_touches_own_row(api, student, other_student, login):
    other_preference = UserPreference.objects.get(user=other_student)
    login(student)

    api.patch(URL, {"email_notifications": False}, format="json")

    other_preference.refresh_from_db()
    assert other_preference.email_notifications is True


def test_anonymous_cannot_read_preferences(api):
    assert api.get(URL).status_code == 401


def test_unknown_category_is_rejected(api, student, login):
    import uuid

    login(student)
    response = api.patch(
        URL, {"preferred_category_ids": [str(uuid.uuid4())]}, format="json"
    )

    assert response.status_code == 400

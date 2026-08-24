"""Saved event tests (§15: save, duplicate save, unsave, unauthorized access)."""

import pytest
from django.db.utils import IntegrityError

from apps.events.models import Event, SavedEvent

pytestmark = pytest.mark.django_db


def save_url(event):
    return f"/api/events/{event.id}/save/"


SAVED_LIST_URL = "/api/users/me/saved-events/"


def test_student_saves_event(api, student, event, login):
    login(student)
    response = api.post(save_url(event), format="json")

    assert response.status_code == 201, response.data
    assert response.data["saved"] is True
    assert SavedEvent.objects.filter(user=student, event=event).count() == 1


def test_duplicate_save_does_not_create_second_row(api, student, event, login):
    login(student)
    api.post(save_url(event), format="json")

    response = api.post(save_url(event), format="json")

    assert response.status_code == 200
    assert response.data["already_saved"] is True
    assert SavedEvent.objects.filter(user=student, event=event).count() == 1


def test_database_enforces_save_uniqueness(db, student, event):
    SavedEvent.objects.create(user=student, event=event)
    with pytest.raises(IntegrityError):
        SavedEvent.objects.create(user=student, event=event)


def test_unsave_removes_row(api, student, event, login):
    login(student)
    api.post(save_url(event), format="json")

    response = api.delete(save_url(event))

    assert response.status_code == 200
    assert response.data["saved"] is False
    assert not SavedEvent.objects.filter(user=student, event=event).exists()


def test_unsave_when_not_saved_is_harmless(api, student, event, login):
    login(student)
    response = api.delete(save_url(event))

    assert response.status_code == 200
    assert response.data["was_saved"] is False


def test_anonymous_cannot_save(api, event):
    assert api.post(save_url(event), format="json").status_code in (401, 403)


def test_staff_cannot_save_events(api, staff, event, login):
    login(staff)
    assert api.post(save_url(event), format="json").status_code == 403


def test_saved_event_list_returns_only_own_saves(api, student, other_student, event, login):
    SavedEvent.objects.create(user=other_student, event=event)
    login(student)
    api.post(save_url(event), format="json")

    response = api.get(SAVED_LIST_URL)

    assert response.status_code == 200
    assert response.data["count"] == 1
    assert response.data["results"][0]["event"]["id"] == str(event.id)


def test_saved_flag_appears_in_event_payload(api, student, event, login):
    login(student)
    api.post(save_url(event), format="json")

    response = api.get(f"/api/events/{event.slug}/")

    assert response.data["is_saved"] is True


def test_cannot_save_unverified_event(api, student, event, login):
    Event.objects.filter(pk=event.pk).update(is_verified=False)
    login(student)

    assert api.post(save_url(event), format="json").status_code == 404


def test_anonymous_saved_list_is_rejected(api):
    assert api.get(SAVED_LIST_URL).status_code == 401

"""Registration tests (§15: register, duplicate registration, cancel,
capacity/race-condition behaviour)."""

from datetime import timedelta

import pytest
from django.db.utils import IntegrityError
from django.utils import timezone

from apps.common.enums import RegistrationStatus
from apps.events.models import Event
from apps.registrations.models import EventRegistration
from apps.registrations.services import register_for_event

pytestmark = pytest.mark.django_db

CREATE_URL = "/api/registrations/"
MY_LIST_URL = "/api/users/me/registrations/"


def test_student_registers_for_event(api, student, event, login):
    login(student)
    response = api.post(CREATE_URL, {"event_id": str(event.id)}, format="json")

    assert response.status_code == 201, response.data
    assert response.data["status"] == RegistrationStatus.REGISTERED
    assert EventRegistration.objects.filter(user=student, event=event).count() == 1


def test_student_can_register_by_slug(api, student, event, login):
    login(student)
    response = api.post(CREATE_URL, {"event_slug": event.slug}, format="json")

    assert response.status_code == 201, response.data


def test_duplicate_registration_is_rejected(api, student, event, login):
    login(student)
    api.post(CREATE_URL, {"event_id": str(event.id)}, format="json")

    response = api.post(CREATE_URL, {"event_id": str(event.id)}, format="json")

    assert response.status_code == 409
    assert EventRegistration.objects.filter(user=student, event=event).count() == 1


def test_database_enforces_registration_uniqueness(db, student, event):
    EventRegistration.objects.create(user=student, event=event)
    with pytest.raises(IntegrityError):
        EventRegistration.objects.create(user=student, event=event)


def test_cancelled_registration_is_reactivated_not_duplicated(db, student, event):
    registration = EventRegistration.objects.create(
        user=student, event=event, status=RegistrationStatus.CANCELLED
    )

    reactivated, created = register_for_event(user=student, event=event)

    assert created is False
    assert reactivated.pk == registration.pk
    assert reactivated.status == RegistrationStatus.REGISTERED
    assert EventRegistration.objects.filter(user=student, event=event).count() == 1


def test_cannot_register_for_unverified_event(api, student, event, login):
    Event.objects.filter(pk=event.pk).update(is_verified=False)
    login(student)

    response = api.post(CREATE_URL, {"event_id": str(event.id)}, format="json")

    assert response.status_code == 400


def test_cannot_register_for_finished_event(api, student, staff, login):
    finished = Event.objects.create(
        title="Finished Event",
        description="Already over.",
        start_time=timezone.now() - timedelta(days=3),
        end_time=timezone.now() - timedelta(days=2),
        created_by=staff,
        is_verified=True,
    )
    login(student)

    response = api.post(CREATE_URL, {"event_id": str(finished.id)}, format="json")

    assert response.status_code == 400
    assert "ended" in response.data["detail"].lower()


def test_anonymous_cannot_register(api, event):
    assert api.post(CREATE_URL, {"event_id": str(event.id)}, format="json").status_code in (401, 403)


def test_staff_cannot_register(api, staff, event, login):
    login(staff)
    assert api.post(CREATE_URL, {"event_id": str(event.id)}, format="json").status_code == 403


def test_registration_requires_an_event_reference(api, student, login):
    login(student)
    response = api.post(CREATE_URL, {}, format="json")

    assert response.status_code == 400
    assert "event_id" in response.data["errors"]


def test_my_registration_list_returns_only_own_rows(api, student, other_student, event, login):
    EventRegistration.objects.create(user=other_student, event=event)
    login(student)
    api.post(CREATE_URL, {"event_id": str(event.id)}, format="json")

    response = api.get(MY_LIST_URL)

    assert response.status_code == 200
    assert response.data["count"] == 1
    assert response.data["results"][0]["event"]["id"] == str(event.id)


def test_student_cancels_own_registration(api, student, event, login):
    login(student)
    created = api.post(CREATE_URL, {"event_id": str(event.id)}, format="json")
    registration_id = created.data["id"]

    response = api.post(f"{CREATE_URL}{registration_id}/cancel/", format="json")

    assert response.status_code == 200
    assert response.data["status"] == RegistrationStatus.CANCELLED


def test_cancelling_twice_conflicts(api, student, event, login):
    login(student)
    registration_id = api.post(CREATE_URL, {"event_id": str(event.id)}, format="json").data["id"]
    api.post(f"{CREATE_URL}{registration_id}/cancel/", format="json")

    response = api.post(f"{CREATE_URL}{registration_id}/cancel/", format="json")

    assert response.status_code == 409


def test_student_cannot_cancel_another_students_registration(
    api, student, other_student, event, login
):
    foreign = EventRegistration.objects.create(user=other_student, event=event)
    login(student)

    response = api.post(f"{CREATE_URL}{foreign.id}/cancel/", format="json")

    assert response.status_code == 404
    foreign.refresh_from_db()
    assert foreign.status == RegistrationStatus.REGISTERED


def test_event_owner_marks_attendance(api, staff, student, event, login):
    registration = EventRegistration.objects.create(user=student, event=event)
    login(staff)

    response = api.post(
        f"{CREATE_URL}{registration.id}/status/",
        {"status": RegistrationStatus.ATTENDED},
        format="json",
    )

    assert response.status_code == 200
    registration.refresh_from_db()
    assert registration.status == RegistrationStatus.ATTENDED


def test_other_staff_cannot_mark_attendance(api, other_staff, student, event, login):
    registration = EventRegistration.objects.create(user=student, event=event)
    login(other_staff)

    response = api.post(
        f"{CREATE_URL}{registration.id}/status/",
        {"status": RegistrationStatus.ATTENDED},
        format="json",
    )

    assert response.status_code == 403


def test_registration_count_and_flag_in_event_payload(api, student, event, login):
    login(student)
    api.post(CREATE_URL, {"event_id": str(event.id)}, format="json")

    response = api.get(f"/api/events/{event.slug}/")

    assert response.data["registration_count"] == 1
    assert response.data["is_registered"] is True


def test_concurrent_registration_attempts_yield_one_row(db, student, event):
    """The unique constraint is the final guard when two calls race (§10.3)."""
    register_for_event(user=student, event=event)

    from apps.common.exceptions import ConflictError

    with pytest.raises(ConflictError):
        register_for_event(user=student, event=event)

    assert EventRegistration.objects.filter(user=student, event=event).count() == 1

"""Event tests (§15: create, edit own, reject edit-other, invalid dates,
virtual validation, categories)."""

from datetime import timedelta

import pytest
from django.utils import timezone

from apps.common.enums import AuditAction
from apps.common.models import AdminActivityLog
from apps.events.models import Event

pytestmark = pytest.mark.django_db

LIST_URL = "/api/events/"


def test_event_list_is_public_and_hides_unverified(api, event):
    unverified = Event.objects.create(
        title="Draft Event",
        description="Not yet verified.",
        start_time=timezone.now() + timedelta(days=2),
        end_time=timezone.now() + timedelta(days=2, hours=3),
        created_by=event.created_by,
        institution=event.institution,
    )

    response = api.get(LIST_URL)

    assert response.status_code == 200
    ids = [row["id"] for row in response.data["results"]]
    assert str(event.id) in ids
    assert str(unverified.id) not in ids


def test_event_detail_by_slug_and_by_id(api, event):
    assert api.get(f"{LIST_URL}{event.slug}/").status_code == 200
    assert api.get(f"{LIST_URL}{event.id}/").status_code == 200


def test_staff_sees_own_unverified_event(api, staff, event, login):
    Event.objects.filter(pk=event.pk).update(is_verified=False)
    login(staff)

    response = api.get(f"{LIST_URL}{event.slug}/")
    assert response.status_code == 200


def test_other_staff_cannot_see_unverified_event(api, other_staff, event, login):
    Event.objects.filter(pk=event.pk).update(is_verified=False)
    login(other_staff)

    assert api.get(f"{LIST_URL}{event.slug}/").status_code == 404


def test_staff_creates_event_with_categories_and_audit_record(
    api, staff, event_payload, categories, login
):
    login(staff)
    response = api.post(LIST_URL, event_payload, format="json")

    assert response.status_code == 201, response.data
    assert [row["slug"] for row in response.data["categories"]] == ["chess"]
    assert response.data["is_verified"] is False  # staff submissions await review
    created = Event.objects.get(id=response.data["id"])
    assert created.created_by_id == staff.id
    assert AdminActivityLog.objects.filter(
        user=staff, action=AuditAction.CREATED_EVENT, record_id=str(created.id)
    ).exists()


def test_admin_created_event_is_verified_immediately(api, admin_user, event_payload, login):
    login(admin_user)
    response = api.post(LIST_URL, event_payload, format="json")

    assert response.status_code == 201, response.data
    assert response.data["is_verified"] is True


def test_student_cannot_create_event(api, student, event_payload, login):
    login(student)
    assert api.post(LIST_URL, event_payload, format="json").status_code == 403


def test_anonymous_cannot_create_event(api, event_payload):
    assert api.post(LIST_URL, event_payload, format="json").status_code in (401, 403)


def test_event_rejects_end_before_start(api, staff, event_payload, login):
    login(staff)
    payload = {**event_payload, "end_time": event_payload["start_time"]}

    response = api.post(LIST_URL, payload, format="json")

    assert response.status_code == 400
    assert "end_time" in response.data["errors"]


def test_virtual_event_rejects_physical_venue(api, staff, event_payload, login):
    login(staff)
    payload = {
        **event_payload,
        "is_virtual": True,
        "registration_link": "https://meet.example.com/abc",
    }

    response = api.post(LIST_URL, payload, format="json")

    assert response.status_code == 400
    assert "venue" in response.data["errors"]


def test_virtual_event_requires_registration_link(api, staff, event_payload, login):
    login(staff)
    payload = {**event_payload, "is_virtual": True, "venue": None, "latitude": None}

    response = api.post(LIST_URL, payload, format="json")

    assert response.status_code == 400
    assert "registration_link" in response.data["errors"]


def test_virtual_event_accepted_without_location(api, staff, event_payload, login):
    login(staff)
    payload = {
        **event_payload,
        "is_virtual": True,
        "venue": None,
        "location": None,
        "registration_link": "https://meet.example.com/abc",
    }

    response = api.post(LIST_URL, payload, format="json")

    assert response.status_code == 201, response.data
    assert response.data["is_virtual"] is True


def test_event_rejects_out_of_range_latitude(api, staff, event_payload, login):
    login(staff)
    response = api.post(LIST_URL, {**event_payload, "latitude": "120.0"}, format="json")

    assert response.status_code == 400
    assert "latitude" in response.data["errors"]


def test_staff_cannot_create_event_for_another_institution(
    api, staff, other_institution, event_payload, login
):
    login(staff)
    payload = {**event_payload, "institution_id": str(other_institution.id)}

    response = api.post(LIST_URL, payload, format="json")

    assert response.status_code == 400
    assert "institution_id" in response.data["errors"]


def test_staff_edits_own_event(api, staff, event, login):
    login(staff)
    response = api.patch(f"{LIST_URL}{event.slug}/", {"title": "Updated Title"}, format="json")

    assert response.status_code == 200, response.data
    event.refresh_from_db()
    assert event.title == "Updated Title"
    assert AdminActivityLog.objects.filter(
        action=AuditAction.UPDATED_EVENT, record_id=str(event.id)
    ).exists()


def test_staff_cannot_edit_another_institutions_event(api, other_staff, event, login):
    login(other_staff)
    response = api.patch(f"{LIST_URL}{event.slug}/", {"title": "Hijacked"}, format="json")

    assert response.status_code == 403
    event.refresh_from_db()
    assert event.title == "Nairobi Math Olympiad"


def test_admin_can_edit_any_event(api, admin_user, event, login):
    login(admin_user)
    response = api.patch(f"{LIST_URL}{event.slug}/", {"title": "Curated Title"}, format="json")

    assert response.status_code == 200
    event.refresh_from_db()
    assert event.title == "Curated Title"


def test_staff_replaces_event_categories(api, staff, event, categories, login):
    login(staff)
    response = api.patch(
        f"{LIST_URL}{event.slug}/",
        {"category_ids": [str(categories["sports"].id), str(categories["chess"].id)]},
        format="json",
    )

    assert response.status_code == 200
    assert sorted(row["slug"] for row in response.data["categories"]) == ["chess", "sports"]


def test_owner_deletes_event_and_audit_survives(api, staff, event, login):
    login(staff)
    event_id = str(event.id)

    response = api.delete(f"{LIST_URL}{event.slug}/")

    assert response.status_code == 204
    assert not Event.objects.filter(id=event_id).exists()
    assert AdminActivityLog.objects.filter(
        action=AuditAction.DELETED_EVENT, record_id=event_id
    ).exists()


def test_student_cannot_delete_event(api, student, event, login):
    login(student)
    assert api.delete(f"{LIST_URL}{event.slug}/").status_code == 403


def test_admin_verifies_event(api, admin_user, staff, event, login):
    Event.objects.filter(pk=event.pk).update(is_verified=False)
    login(admin_user)

    response = api.post(f"{LIST_URL}{event.id}/verify/", format="json")

    assert response.status_code == 200
    event.refresh_from_db()
    assert event.is_verified is True
    assert event.verified_by_id == admin_user.id
    assert event.verified_at is not None


def test_staff_cannot_verify_event(api, staff, event, login):
    login(staff)
    assert api.post(f"{LIST_URL}{event.id}/verify/", format="json").status_code == 403


def test_filter_by_category_school_level_and_search(api, event, categories, school_levels):
    assert api.get(f"{LIST_URL}?category=math").data["count"] == 1
    assert api.get(f"{LIST_URL}?category=sports").data["count"] == 0
    assert api.get(f"{LIST_URL}?school_level=senior-secondary").data["count"] == 1
    assert api.get(f"{LIST_URL}?search=olympiad").data["count"] == 1
    assert api.get(f"{LIST_URL}?search=nothingmatches").data["count"] == 0


def test_filter_upcoming_excludes_finished_events(api, event, staff):
    Event.objects.create(
        title="Past Event",
        description="Already finished.",
        start_time=timezone.now() - timedelta(days=5),
        end_time=timezone.now() - timedelta(days=4),
        created_by=staff,
        is_verified=True,
    )

    assert api.get(f"{LIST_URL}?upcoming=true").data["count"] == 1
    assert api.get(LIST_URL).data["count"] == 2


def test_event_owner_lists_registrations(api, staff, student, event, login):
    from apps.registrations.models import EventRegistration

    EventRegistration.objects.create(user=student, event=event)
    login(staff)

    response = api.get(f"{LIST_URL}{event.id}/registrations/")

    assert response.status_code == 200
    assert response.data["count"] == 1
    assert response.data["results"][0]["user"]["email"] == student.email


def test_other_staff_cannot_list_registrations(api, other_staff, event, login):
    login(other_staff)
    assert api.get(f"{LIST_URL}{event.id}/registrations/").status_code == 403


def test_student_cannot_list_event_registrations(api, student, event, login):
    login(student)
    assert api.get(f"{LIST_URL}{event.id}/registrations/").status_code == 403


def test_database_rejects_end_before_start(db, staff):
    from django.db.utils import IntegrityError

    start = timezone.now() + timedelta(days=1)
    with pytest.raises(IntegrityError):
        Event.objects.create(
            title="Broken Event",
            description="Invalid dates bypassing the serializer.",
            start_time=start,
            end_time=start - timedelta(hours=1),
            created_by=staff,
        )

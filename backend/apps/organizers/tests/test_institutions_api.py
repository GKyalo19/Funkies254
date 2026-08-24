"""Institution tests (§15: create, verify, staff ownership, admin access)."""

import pytest

from apps.common.enums import AuditAction
from apps.common.models import AdminActivityLog
from apps.organizers.models import Institution

pytestmark = pytest.mark.django_db

LIST_URL = "/api/institutions/"


def test_institution_list_is_public(api, institution):
    response = api.get(LIST_URL)

    assert response.status_code == 200
    assert response.data["count"] == 1


def test_institution_detail_is_public_and_uses_slug(api, institution):
    response = api.get(f"{LIST_URL}{institution.slug}/")

    assert response.status_code == 200
    assert response.data["name"] == institution.name


def test_admin_creates_institution_with_generated_slug(api, admin_user, login):
    login(admin_user)
    response = api.post(
        LIST_URL,
        {"name": "Kisumu Girls High School", "location": "Kisumu"},
        format="json",
    )

    assert response.status_code == 201, response.data
    institution = Institution.objects.get(name="Kisumu Girls High School")
    assert institution.slug == "kisumu-girls-high-school"
    assert institution.verified is False
    assert institution.created_by_id == admin_user.id


def test_student_cannot_create_institution(api, student, login):
    login(student)
    response = api.post(LIST_URL, {"name": "Fake School"}, format="json")

    assert response.status_code == 403


def test_staff_cannot_create_institution(api, staff, login):
    login(staff)
    assert api.post(LIST_URL, {"name": "Another School"}, format="json").status_code == 403


def test_staff_updates_own_institution(api, staff, institution, login):
    login(staff)
    response = api.patch(
        f"{LIST_URL}{institution.slug}/", {"phone": "+254700111222"}, format="json"
    )

    assert response.status_code == 200, response.data
    institution.refresh_from_db()
    assert institution.phone == "+254700111222"


def test_staff_cannot_update_another_institution(api, staff, other_institution, login):
    login(staff)
    response = api.patch(
        f"{LIST_URL}{other_institution.slug}/", {"phone": "+254700333444"}, format="json"
    )

    assert response.status_code == 403
    other_institution.refresh_from_db()
    assert other_institution.phone is None


def test_student_cannot_update_institution(api, student, institution, login):
    login(student)
    assert (
        api.patch(f"{LIST_URL}{institution.slug}/", {"name": "Hacked"}, format="json").status_code
        == 403
    )


def test_anonymous_cannot_update_institution(api, institution):
    assert api.patch(f"{LIST_URL}{institution.slug}/", {"name": "Hacked"}, format="json").status_code in (
        401,
        403,
    )


def test_admin_verifies_institution_and_logs_action(api, admin_user, other_institution, login):
    other_institution.verified = False
    other_institution.save(update_fields=["verified"])
    login(admin_user)

    response = api.post(f"{LIST_URL}{other_institution.slug}/verify/", format="json")

    assert response.status_code == 200
    other_institution.refresh_from_db()
    assert other_institution.verified is True
    assert AdminActivityLog.objects.filter(
        user=admin_user,
        action=AuditAction.VERIFIED_INSTITUTION,
        record_id=str(other_institution.id),
    ).exists()


def test_staff_cannot_verify_institution(api, staff, institution, login):
    login(staff)
    assert api.post(f"{LIST_URL}{institution.slug}/verify/", format="json").status_code == 403


def test_slug_collision_gets_suffix(db, institution):
    duplicate = Institution.objects.create(name="Nairobi High School")
    assert duplicate.slug == "nairobi-high-school-2"

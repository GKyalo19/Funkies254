"""Admin account management and the audit records it must produce (§10.5, §13)."""

import pytest

from apps.common.enums import AuditAction, UserRole
from apps.common.models import AdminActivityLog

pytestmark = pytest.mark.django_db


def test_admin_can_list_users(api, admin_user, student, login):
    login(admin_user)
    response = api.get("/api/users/")

    assert response.status_code == 200
    emails = [row["email"] for row in response.data["results"]]
    assert student.email in emails


def test_student_cannot_list_users(api, student, login):
    login(student)
    assert api.get("/api/users/").status_code == 403


def test_admin_suspends_user_and_writes_audit_record(api, admin_user, student, login):
    login(admin_user)
    response = api.post(f"/api/users/{student.id}/suspend/", format="json")

    assert response.status_code == 200
    student.refresh_from_db()
    assert student.is_active is False
    assert AdminActivityLog.objects.filter(
        user=admin_user, action=AuditAction.SUSPENDED_USER, record_id=str(student.id)
    ).exists()


def test_admin_reinstates_user(api, admin_user, student, login):
    student.is_active = False
    student.save(update_fields=["is_active"])
    login(admin_user)

    response = api.post(f"/api/users/{student.id}/reinstate/", format="json")

    assert response.status_code == 200
    student.refresh_from_db()
    assert student.is_active is True


def test_admin_cannot_suspend_another_admin(api, admin_user, super_admin, login):
    login(admin_user)
    response = api.post(f"/api/users/{super_admin.id}/suspend/", format="json")

    assert response.status_code == 403
    super_admin.refresh_from_db()
    assert super_admin.is_active is True


def test_admin_cannot_grant_admin_role(api, admin_user, student, login):
    login(admin_user)
    response = api.post(f"/api/users/{student.id}/role/", {"role": "admin"}, format="json")

    assert response.status_code == 403
    student.refresh_from_db()
    assert student.role == UserRole.STUDENT


def test_super_admin_can_create_admin_and_logs_it(api, super_admin, student, login):
    login(super_admin)
    response = api.post(f"/api/users/{student.id}/role/", {"role": "admin"}, format="json")

    assert response.status_code == 200, response.data
    student.refresh_from_db()
    assert student.role == UserRole.ADMIN
    assert student.is_staff is True
    assert AdminActivityLog.objects.filter(
        action=AuditAction.CREATED_ADMIN, record_id=str(student.id)
    ).exists()


def test_super_admin_can_remove_admin(api, super_admin, admin_user, login):
    login(super_admin)
    response = api.post(f"/api/users/{admin_user.id}/role/", {"role": "student"}, format="json")

    assert response.status_code == 200
    admin_user.refresh_from_db()
    assert admin_user.role == UserRole.STUDENT
    assert admin_user.is_staff is False
    assert AdminActivityLog.objects.filter(
        action=AuditAction.REMOVED_ADMIN, record_id=str(admin_user.id)
    ).exists()


def test_admin_cannot_promote_student_to_institution_staff(api, admin_user, student, login):
    login(admin_user)
    response = api.post(
        f"/api/users/{student.id}/role/", {"role": "institution_staff"}, format="json"
    )

    assert response.status_code == 403
    student.refresh_from_db()
    assert student.role == UserRole.STUDENT


def test_super_admin_promotes_staff_from_affiliation(api, super_admin, other_student, login):
    other_student.institution_affiliation = "Alliance High School"
    other_student.save(update_fields=["institution_affiliation"])
    login(super_admin)

    response = api.post(
        f"/api/users/{other_student.id}/role/", {"role": "institution_staff"}, format="json"
    )

    assert response.status_code == 200, response.data
    other_student.refresh_from_db()
    assert other_student.role == UserRole.INSTITUTION_STAFF
    assert other_student.institution_id is not None
    assert other_student.institution.name == "Alliance High School"


def test_super_admin_promotes_staff_with_institution_id(
    api, super_admin, other_student, institution, login
):
    login(super_admin)
    response = api.post(
        f"/api/users/{other_student.id}/role/",
        {"role": "institution_staff", "institution_id": str(institution.id)},
        format="json",
    )

    assert response.status_code == 200, response.data
    other_student.refresh_from_db()
    assert other_student.role == UserRole.INSTITUTION_STAFF
    assert other_student.institution_id == institution.id
    assert other_student.institution_affiliation == institution.name


def test_staff_promotion_requires_an_institution(api, super_admin, other_student, login):
    login(super_admin)
    response = api.post(
        f"/api/users/{other_student.id}/role/", {"role": "institution_staff"}, format="json"
    )

    assert response.status_code == 400
    other_student.refresh_from_db()
    assert other_student.role == UserRole.STUDENT


def test_admin_can_filter_users_by_affiliation(api, admin_user, student, login):
    student.institution_affiliation = "Nairobi High School"
    student.save(update_fields=["institution_affiliation"])
    login(admin_user)

    response = api.get("/api/users/?affiliation=nairobi")

    assert response.status_code == 200
    emails = [row["email"] for row in response.data["results"]]
    assert student.email in emails


def test_admin_can_retrieve_user(api, admin_user, student, login):
    login(admin_user)
    response = api.get(f"/api/users/{student.id}/")

    assert response.status_code == 200
    assert response.data["email"] == student.email
    assert "institution_affiliation" in response.data


def test_admin_cannot_patch_user(api, admin_user, student, login):
    login(admin_user)
    response = api.patch(f"/api/users/{student.id}/", {"name": "Nope"}, format="json")

    assert response.status_code == 403


def test_super_admin_can_patch_user_profile(api, super_admin, other_student, login):
    login(super_admin)
    response = api.patch(
        f"/api/users/{other_student.id}/",
        {"name": "Patched Student", "institution_affiliation": "Strathmore University"},
        format="json",
    )

    assert response.status_code == 200, response.data
    other_student.refresh_from_db()
    assert other_student.name == "Patched Student"
    assert other_student.institution_affiliation == "Strathmore University"


def test_activity_log_endpoint_is_admin_only(api, admin_user, student, other_student, login):
    login(admin_user)
    api.post(f"/api/users/{other_student.id}/suspend/", format="json")
    assert api.get("/api/admin/activity-logs/").status_code == 200

    api.post("/api/auth/logout/", format="json")
    login(student)
    assert api.get("/api/admin/activity-logs/").status_code == 403

"""Role boundary tests (§15: student/staff/admin/super-admin boundaries)."""

import pytest

from apps.common.enums import ADMIN_ROLES, PRIVILEGED_ROLES, AuditAction, UserRole

pytestmark = pytest.mark.django_db


def test_role_vocabulary_matches_the_specification():
    assert [role.value for role in UserRole] == [
        "student",
        "institution_staff",
        "admin",
        "super_admin",
    ]
    assert set(ADMIN_ROLES) == {UserRole.ADMIN, UserRole.SUPER_ADMIN}
    assert UserRole.STUDENT not in PRIVILEGED_ROLES


def test_audit_vocabulary_contains_the_documented_actions():
    for action in (
        "created_event",
        "updated_event",
        "deleted_event",
        "verified_institution",
        "promoted_user",
        "suspended_user",
        "created_admin",
        "removed_admin",
    ):
        assert action in AuditAction.values


def test_role_properties(student, staff, admin_user, super_admin):
    assert student.is_student and not student.is_platform_admin
    assert staff.is_institution_staff
    assert admin_user.is_platform_admin and not admin_user.is_super_admin
    assert super_admin.is_platform_admin and super_admin.is_super_admin


@pytest.mark.parametrize(
    "fixture_name,expected",
    [
        ("student", 403),
        ("staff", 201),
        ("admin_user", 201),
        ("super_admin", 201),
    ],
)
def test_event_creation_boundary(api, request, fixture_name, expected, event_payload, login):
    user = request.getfixturevalue(fixture_name)
    login(user)

    payload = dict(event_payload)
    if not user.is_institution_staff:
        payload.pop("institution_id", None)

    response = api.post("/api/events/", payload, format="json")

    assert response.status_code == expected, response.data


@pytest.mark.parametrize(
    "fixture_name,expected",
    [("student", 403), ("staff", 403), ("admin_user", 200), ("super_admin", 200)],
)
def test_activity_log_visibility_boundary(api, request, fixture_name, expected, login):
    login(request.getfixturevalue(fixture_name))

    assert api.get("/api/admin/activity-logs/").status_code == expected


@pytest.mark.parametrize(
    "fixture_name,expected",
    [
        ("student", 403),  # not an administrator at all
        ("staff", 403),
        ("admin_user", 403),  # role changes are super-admin only
        ("super_admin", 200),
    ],
)
def test_granting_admin_role_is_super_admin_only(
    api, request, fixture_name, expected, other_student, login
):
    login(request.getfixturevalue(fixture_name))

    response = api.post(
        f"/api/users/{other_student.id}/role/", {"role": "admin"}, format="json"
    )

    assert response.status_code == expected, response.data


def test_error_responses_use_the_shared_envelope(api, student, login):
    login(student)
    response = api.post("/api/events/", {"title": ""}, format="json")

    assert response.status_code == 403
    assert set(response.data) >= {"detail", "code"}

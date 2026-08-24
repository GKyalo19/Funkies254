"""
Central controlled vocabularies.

Every role, status and audit action used anywhere in the project is defined
here exactly once so filtering, analytics and tests stay consistent (§13, §18).
"""

from django.db import models


class UserRole(models.TextChoices):
    STUDENT = "student", "Student"
    INSTITUTION_STAFF = "institution_staff", "Institution staff"
    ADMIN = "admin", "Admin"
    SUPER_ADMIN = "super_admin", "Super admin"


#: Roles that may curate events and institutions.
PRIVILEGED_ROLES = (
    UserRole.INSTITUTION_STAFF,
    UserRole.ADMIN,
    UserRole.SUPER_ADMIN,
)

#: Roles with platform-wide administrative reach.
ADMIN_ROLES = (UserRole.ADMIN, UserRole.SUPER_ADMIN)

#: Roles a user may self-select at registration. Elevated roles are granted by
#: an admin, never claimed by the registrant.
SELF_ASSIGNABLE_ROLES = (UserRole.STUDENT,)


class RegistrationStatus(models.TextChoices):
    REGISTERED = "registered", "Registered"
    ATTENDED = "attended", "Attended"
    CANCELLED = "cancelled", "Cancelled"


class AuditAction(models.TextChoices):
    CREATED_EVENT = "created_event", "Created event"
    UPDATED_EVENT = "updated_event", "Updated event"
    DELETED_EVENT = "deleted_event", "Deleted event"
    VERIFIED_EVENT = "verified_event", "Verified event"
    CREATED_INSTITUTION = "created_institution", "Created institution"
    UPDATED_INSTITUTION = "updated_institution", "Updated institution"
    VERIFIED_INSTITUTION = "verified_institution", "Verified institution"
    PROMOTED_USER = "promoted_user", "Promoted user"
    SUSPENDED_USER = "suspended_user", "Suspended user"
    REINSTATED_USER = "reinstated_user", "Reinstated user"
    CREATED_ADMIN = "created_admin", "Created admin"
    REMOVED_ADMIN = "removed_admin", "Removed admin"


class SchoolLevelSlug(models.TextChoices):
    """Reference rows seeded by ``seed_demo_data``; the table stays extensible."""

    PRIMARY = "primary", "Primary"
    JUNIOR_SECONDARY = "junior-secondary", "Junior Secondary"
    SENIOR_SECONDARY = "senior-secondary", "Senior Secondary"
    COLLEGE = "college", "College"

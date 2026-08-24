"""
DRF permission classes for the four application roles (§6).

Role permissions answer "may this kind of user do this kind of thing"; the
object-level classes additionally answer "does this user own this record", so a
staff account can never edit another institution's event.
"""

from rest_framework.permissions import SAFE_METHODS, BasePermission, IsAuthenticated

from apps.common.enums import ADMIN_ROLES, PRIVILEGED_ROLES, UserRole

__all__ = [
    "IsAuthenticated",
    "IsStudent",
    "IsInstitutionStaff",
    "IsAdmin",
    "IsSuperAdmin",
    "IsStaffOrReadOnly",
    "IsEventOwner",
    "IsInstitutionOwner",
]


def _role(user):
    return getattr(user, "role", None)


def _is_active_user(user):
    return bool(user and user.is_authenticated and user.is_active)


def _is_admin(user):
    return _is_active_user(user) and _role(user) in ADMIN_ROLES


class _RolePermission(BasePermission):
    allowed_roles: tuple = ()

    def has_permission(self, request, view):
        return _is_active_user(request.user) and _role(request.user) in self.allowed_roles


class IsStudent(_RolePermission):
    message = "Only student accounts may perform this action."
    allowed_roles = (UserRole.STUDENT,)


class IsInstitutionStaff(_RolePermission):
    message = "Only institution staff may perform this action."
    allowed_roles = (UserRole.INSTITUTION_STAFF,)


class IsAdmin(_RolePermission):
    message = "Administrator privileges are required."
    allowed_roles = ADMIN_ROLES


class IsSuperAdmin(_RolePermission):
    message = "Super administrator privileges are required."
    allowed_roles = (UserRole.SUPER_ADMIN,)


class IsStaffOrReadOnly(BasePermission):
    """Anyone may read; only institution staff and admins may write."""

    message = "Only institution staff or administrators may modify this resource."

    def has_permission(self, request, view):
        if request.method in SAFE_METHODS:
            return True
        return _is_active_user(request.user) and _role(request.user) in PRIVILEGED_ROLES


class IsEventOwner(BasePermission):
    """
    Object-level ownership for events.

    Admins may curate any event. Institution staff may only touch events they
    created or events belonging to their own institution.
    """

    message = "You may only modify events belonging to your own institution."

    def has_object_permission(self, request, view, obj):
        if request.method in SAFE_METHODS:
            return True
        user = request.user
        if _is_admin(user):
            return True
        if not _is_active_user(user) or _role(user) != UserRole.INSTITUTION_STAFF:
            return False
        if obj.created_by_id == user.id:
            return True
        return bool(user.institution_id) and obj.institution_id == user.institution_id


class IsInstitutionOwner(BasePermission):
    """Object-level ownership for institution profiles."""

    message = "You may only modify your own institution."

    def has_object_permission(self, request, view, obj):
        if request.method in SAFE_METHODS:
            return True
        user = request.user
        if _is_admin(user):
            return True
        if not _is_active_user(user) or _role(user) != UserRole.INSTITUTION_STAFF:
            return False
        return bool(user.institution_id) and obj.id == user.institution_id

"""Reusable DRF permission classes shared across apps."""
from rest_framework.permissions import SAFE_METHODS, BasePermission


class IsStaffOrReadOnly(BasePermission):
    """
    Anyone (even anonymous visitors) can read events/organizers/categories.
    Only staff accounts (curators/admins, managed via Django admin) can
    create, update, or delete them. Regular students never get write access
    to this content — event data is curated, not user-generated, by design.
    """

    def has_permission(self, request, view):
        if request.method in SAFE_METHODS:
            return True
        return bool(request.user and request.user.is_authenticated and request.user.is_staff)


class IsOwner(BasePermission):
    """Object-level check: the request user must be the `user` field owner."""

    def has_object_permission(self, request, view, obj):
        return getattr(obj, "user_id", None) == getattr(request.user, "id", None)

"""
User lifecycle services (§10.5).

Multi-step workflows live here so views stay thin and every write that must be
all-or-nothing runs inside one transaction.
"""

from django.db import transaction

from apps.common.audit import log_action
from apps.common.enums import ADMIN_ROLES, AuditAction, UserRole
from apps.users.models import User


@transaction.atomic
def register_user(*, email, name, password, institution_id=None, role=UserRole.STUDENT):
    """Create an account together with its single preference record (§8.1)."""
    from apps.preferences.models import UserPreference

    user = User.objects.create_user(
        email=email,
        password=password,
        name=name,
        role=role,
        institution_id=institution_id,
    )
    UserPreference.objects.create(user=user)
    return user


@transaction.atomic
def set_user_active(*, actor, user, is_active: bool):
    """Suspend or reinstate an account and record who did it."""
    user.is_active = is_active
    user.save(update_fields=["is_active", "updated_at"])
    log_action(
        actor=actor,
        action=AuditAction.REINSTATED_USER if is_active else AuditAction.SUSPENDED_USER,
        instance=user,
    )
    return user


@transaction.atomic
def change_user_role(*, actor, user, role):
    """Change an account's application role and log the correct audit action."""
    previous_role = user.role
    user.role = role
    # Application role and Django admin access are kept in step.
    user.is_staff = role in ADMIN_ROLES
    user.is_superuser = role == UserRole.SUPER_ADMIN
    user.save(update_fields=["role", "is_staff", "is_superuser", "updated_at"])

    if role in ADMIN_ROLES and previous_role not in ADMIN_ROLES:
        action = AuditAction.CREATED_ADMIN
    elif previous_role in ADMIN_ROLES and role not in ADMIN_ROLES:
        action = AuditAction.REMOVED_ADMIN
    else:
        action = AuditAction.PROMOTED_USER

    log_action(actor=actor, action=action, instance=user)
    return user

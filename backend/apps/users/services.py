"""
User lifecycle services (§10.5).

Multi-step workflows live here so views stay thin and every write that must be
all-or-nothing runs inside one transaction.
"""

import hashlib
import hmac
import secrets
from datetime import timedelta

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from apps.common.audit import log_action
from apps.common.enums import ADMIN_ROLES, AuditAction, UserRole
from apps.common.exceptions import BusinessRuleError
from apps.common.mail import send_verification_code_email
from apps.users.models import User


def _hash_verification_code(user_id, code: str) -> str:
    material = f"{settings.SECRET_KEY}:{user_id}:{code}".encode()
    return hashlib.sha256(material).hexdigest()


def issue_and_send_verification_code(user: User, *, force: bool = False) -> None:
    """Create a 6-digit code, store only its hash, and email the plaintext."""
    if user.email_verified:
        raise BusinessRuleError("This email is already verified.")

    now = timezone.now()
    wait = timedelta(seconds=settings.EMAIL_VERIFICATION_RESEND_SECONDS)
    if (
        not force
        and user.email_verification_sent_at
        and now - user.email_verification_sent_at < wait
    ):
        raise BusinessRuleError("Please wait a minute before requesting another code.")

    code = f"{secrets.randbelow(1_000_000):06d}"
    user.email_verification_code_hash = _hash_verification_code(user.id, code)
    user.email_verification_sent_at = now
    user.email_verification_attempts = 0
    user.save(
        update_fields=[
            "email_verification_code_hash",
            "email_verification_sent_at",
            "email_verification_attempts",
            "updated_at",
        ]
    )
    send_verification_code_email(user, code)


def verify_email_code(*, email: str, code: str) -> User:
    """Mark the account verified when the submitted code matches and is still live."""
    normalized = User.objects.normalize_login_email(email)
    user = User.objects.filter(email=normalized).first()
    if user is None:
        raise BusinessRuleError("Invalid verification code.", code="invalid_verification_code")
    if user.email_verified:
        return user
    if not user.email_verification_code_hash or not user.email_verification_sent_at:
        raise BusinessRuleError("Request a new verification code.", code="no_verification_code")

    ttl = timedelta(minutes=settings.EMAIL_VERIFICATION_CODE_TTL_MINUTES)
    if timezone.now() > user.email_verification_sent_at + ttl:
        raise BusinessRuleError(
            "That code has expired. Request a new one.", code="expired_verification_code"
        )

    if user.email_verification_attempts >= settings.EMAIL_VERIFICATION_MAX_ATTEMPTS:
        raise BusinessRuleError(
            "Too many attempts. Request a new code.", code="too_many_verification_attempts"
        )

    user.email_verification_attempts += 1
    user.save(update_fields=["email_verification_attempts", "updated_at"])

    expected = _hash_verification_code(user.id, code)
    if not hmac.compare_digest(user.email_verification_code_hash, expected):
        raise BusinessRuleError("Invalid verification code.", code="invalid_verification_code")

    user.email_verified = True
    user.email_verification_code_hash = ""
    user.email_verification_attempts = 0
    user.save(
        update_fields=[
            "email_verified",
            "email_verification_code_hash",
            "email_verification_attempts",
            "updated_at",
        ]
    )
    return user


def register_user(*, email, name, password, institution_affiliation=None, role=UserRole.STUDENT):
    """Create an account together with its single preference record (§8.1)."""
    from apps.preferences.models import UserPreference

    affiliation = (institution_affiliation or "").strip() or None

    with transaction.atomic():
        user = User.objects.create_user(
            email=email,
            password=password,
            name=name,
            role=role,
            institution_id=None,
            institution_affiliation=affiliation,
            email_verified=False,
        )
        UserPreference.objects.create(user=user)

    issue_and_send_verification_code(user, force=True)
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
def change_user_role(*, actor, user, role, institution_id=None):
    """Change an account's application role and log the correct audit action."""
    from apps.common.exceptions import BusinessRuleError
    from apps.organizers.models import Institution
    from apps.organizers.services import get_or_create_institution_by_name

    previous_role = user.role
    user.role = role
    # Application role and Django admin access are kept in step.
    user.is_staff = role in ADMIN_ROLES
    user.is_superuser = role == UserRole.SUPER_ADMIN

    update_fields = ["role", "is_staff", "is_superuser", "updated_at"]

    if role == UserRole.INSTITUTION_STAFF:
        institution = None
        if institution_id:
            institution = Institution.objects.filter(pk=institution_id).first()
            if institution is None:
                raise BusinessRuleError("Institution does not exist.")
        elif user.institution_id:
            institution = user.institution
        elif user.institution_affiliation:
            institution = get_or_create_institution_by_name(
                name=user.institution_affiliation, actor=actor
            )
        if institution is None:
            raise BusinessRuleError(
                "Link this account to an institution before promoting them to staff."
            )
        user.institution = institution
        update_fields.append("institution")
        if not (user.institution_affiliation or "").strip():
            user.institution_affiliation = institution.name
            update_fields.append("institution_affiliation")

    user.save(update_fields=update_fields)

    if role in ADMIN_ROLES and previous_role not in ADMIN_ROLES:
        action = AuditAction.CREATED_ADMIN
    elif previous_role in ADMIN_ROLES and role not in ADMIN_ROLES:
        action = AuditAction.REMOVED_ADMIN
    else:
        action = AuditAction.PROMOTED_USER

    log_action(actor=actor, action=action, instance=user)
    return user

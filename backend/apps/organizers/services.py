"""Institution workflows (§10.4)."""

from django.db import transaction

from apps.common.audit import log_action
from apps.common.enums import AuditAction
from apps.organizers.models import Institution


def get_or_create_institution_by_name(*, name, actor=None) -> Institution:
    """Reuse an existing institution (case-insensitive name) or create one."""
    cleaned = (name or "").strip()
    if not cleaned:
        raise ValueError("An institution name is required.")
    existing = Institution.objects.filter(name__iexact=cleaned).first()
    if existing is not None:
        return existing
    return create_institution(actor=actor, name=cleaned)


@transaction.atomic
def create_institution(*, actor, **fields) -> Institution:
    institution = Institution.objects.create(created_by=actor, **fields)
    log_action(actor=actor, action=AuditAction.CREATED_INSTITUTION, instance=institution)
    return institution


@transaction.atomic
def update_institution(*, actor, institution: Institution, **fields) -> Institution:
    for field, value in fields.items():
        setattr(institution, field, value)
    institution.save()
    log_action(actor=actor, action=AuditAction.UPDATED_INSTITUTION, instance=institution)
    return institution


@transaction.atomic
def set_institution_verified(*, actor, institution: Institution, verified: bool) -> Institution:
    """Admin verification decision (§10.4)."""
    institution.verified = verified
    institution.save(update_fields=["verified", "updated_at"])
    if verified:
        log_action(
            actor=actor, action=AuditAction.VERIFIED_INSTITUTION, instance=institution
        )
    else:
        log_action(
            actor=actor, action=AuditAction.UPDATED_INSTITUTION, instance=institution
        )
    return institution

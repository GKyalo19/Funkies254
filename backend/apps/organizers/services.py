"""Institution workflows (§10.4)."""

from django.db import transaction

from apps.common.audit import log_action
from apps.common.enums import AuditAction
from apps.organizers.models import Institution


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

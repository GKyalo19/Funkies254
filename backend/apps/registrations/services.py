"""
Registration transactions (§10.3).

The whole flow runs inside one atomic block: the event row is locked, the event
is re-checked, and only then is the registration written. Capacity is not part
of the confirmed schema (§20), so the seat-counting hook is marked but empty.
"""

from django.db import transaction
from django.utils import timezone

from apps.common.db import for_update
from apps.common.enums import RegistrationStatus
from apps.common.exceptions import BusinessRuleError, ConflictError
from apps.events.models import Event
from apps.registrations.models import EventRegistration


@transaction.atomic
def register_for_event(*, user, event_id=None, event=None) -> tuple:
    """
    Register ``user`` for an event.

    Returns ``(registration, created)``. A previously cancelled registration is
    reactivated rather than duplicated, because the database enforces one row
    per (user, event).
    """
    locked = for_update(Event.objects.filter(pk=event_id or event.pk))
    event = locked.first()
    if event is None:
        raise BusinessRuleError("Event does not exist.")

    _assert_open_for_registration(event)

    registration = EventRegistration.objects.filter(user=user, event=event).first()
    if registration is not None:
        if registration.status == RegistrationStatus.REGISTERED:
            raise ConflictError("You are already registered for this event.")
        registration.status = RegistrationStatus.REGISTERED
        registration.save(update_fields=["status"])
        return registration, False

    # Capacity hook: when Event gains a capacity field, count active
    # registrations here — the event row is already locked.
    registration = EventRegistration.objects.create(
        user=user, event=event, status=RegistrationStatus.REGISTERED
    )
    return registration, True


@transaction.atomic
def cancel_registration(*, registration: EventRegistration) -> EventRegistration:
    if registration.status == RegistrationStatus.CANCELLED:
        raise ConflictError("This registration is already cancelled.")
    registration.status = RegistrationStatus.CANCELLED
    registration.save(update_fields=["status"])
    return registration


@transaction.atomic
def set_registration_status(*, registration: EventRegistration, status: str) -> EventRegistration:
    """Used by event owners to mark attendance."""
    if status not in RegistrationStatus.values:
        raise BusinessRuleError("Unknown registration status.")
    registration.status = status
    registration.save(update_fields=["status"])
    return registration


def _assert_open_for_registration(event: Event) -> None:
    if not event.is_verified:
        raise BusinessRuleError("This event is not open for registration yet.")
    if event.end_time <= timezone.now():
        raise BusinessRuleError("This event has already ended.")

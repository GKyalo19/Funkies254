"""
Event services (§10.1, §10.2).

Views delegate here so that multi-table writes are transactional and audit
records are never forgotten. Media uploads happen before the transaction opens
so a slow network call never holds a database transaction open.
"""

from django.db import transaction
from django.utils import timezone

from apps.common import supabase_storage
from apps.common.audit import log_action
from apps.common.enums import AuditAction, UserRole
from apps.common.mail import send_new_event_match_email
from apps.events.models import Event, EventCategory, SavedEvent


def _upload_cover(cover_image, event_id=None):
    supabase_storage.validate_image(cover_image)
    path = supabase_storage.build_object_path("events", cover_image, event_id)
    return supabase_storage.EVENT_COVERS, path


def create_event(*, actor, categories=None, cover_image=None, **fields) -> Event:
    cover_url = None
    if cover_image is not None:
        bucket, path = _upload_cover(cover_image)
        cover_url = supabase_storage.upload(bucket, path, cover_image)

    with transaction.atomic():
        if cover_url:
            fields["cover_image_url"] = cover_url
        # Admin-curated events go live immediately; staff submissions wait for
        # administrator verification (§1.1).
        if actor.is_platform_admin:
            fields.update(
                is_verified=True, verified_by=actor, verified_at=timezone.now()
            )

        event = Event.objects.create(created_by=actor, **fields)
        _set_categories(event, categories)
        log_action(actor=actor, action=AuditAction.CREATED_EVENT, instance=event)

    if event.is_verified:
        notify_users_of_matching_event(event, actor=actor)

    return event


def update_event(*, actor, event: Event, categories=None, cover_image=None, **fields) -> Event:
    cover_url = None
    if cover_image is not None:
        bucket, path = _upload_cover(cover_image, event.id)
        cover_url = supabase_storage.replace(bucket, event.cover_image_url, path, cover_image)

    with transaction.atomic():
        if cover_url:
            fields["cover_image_url"] = cover_url
        for field, value in fields.items():
            setattr(event, field, value)
        event.save()
        if categories is not None:
            _set_categories(event, categories, replace=True)
        log_action(actor=actor, action=AuditAction.UPDATED_EVENT, instance=event)

    return event


@transaction.atomic
def delete_event(*, actor, event: Event) -> None:
    table_name, record_id = event._meta.db_table, str(event.pk)
    cover_url = event.cover_image_url
    event.delete()
    log_action(
        actor=actor,
        action=AuditAction.DELETED_EVENT,
        table_name=table_name,
        record_id=record_id,
    )
    path = supabase_storage.path_from_url(supabase_storage.EVENT_COVERS, cover_url)
    if path and supabase_storage.is_configured():
        transaction.on_commit(lambda: supabase_storage.delete(supabase_storage.EVENT_COVERS, path))


def notify_users_of_matching_event(event: Event, *, actor=None) -> int:
    """Email students whose saved preferences overlap this event's categories."""
    from django.db.models import Q

    from apps.preferences.models import UserPreference

    event_category_ids = set(event.categories.values_list("id", flat=True))
    if not event_category_ids:
        return 0

    queryset = (
        UserPreference.objects.filter(
            email_notifications=True,
            user__is_active=True,
            user__email_verified=True,
            user__role=UserRole.STUDENT,
        )
        .select_related("user")
        .prefetch_related("preferred_categories")
    )
    if actor is not None:
        queryset = queryset.exclude(user=actor)
    if event.school_level_id:
        queryset = queryset.filter(
            Q(school_level_id=event.school_level_id) | Q(school_level_id__isnull=True)
        )

    sent = 0
    for preference in queryset:
        preferred_ids = {category.id for category in preference.preferred_categories.all()}
        if not preferred_ids or preferred_ids.isdisjoint(event_category_ids):
            continue
        if send_new_event_match_email(preference.user, event):
            sent += 1
    return sent


def set_event_verified(*, actor, event: Event, verified: bool) -> Event:
    was_verified = event.is_verified
    with transaction.atomic():
        event.is_verified = verified
        event.verified_by = actor if verified else None
        event.verified_at = timezone.now() if verified else None
        event.save(update_fields=["is_verified", "verified_by", "verified_at", "updated_at"])
        log_action(
            actor=actor,
            action=AuditAction.VERIFIED_EVENT if verified else AuditAction.UPDATED_EVENT,
            instance=event,
        )
    if verified and not was_verified:
        notify_users_of_matching_event(event, actor=actor)
    return event


def _set_categories(event: Event, categories, *, replace=False) -> None:
    if categories is None:
        return
    if replace:
        EventCategory.objects.filter(event=event).delete()
    EventCategory.objects.bulk_create(
        [EventCategory(event=event, category=category) for category in categories],
        ignore_conflicts=True,
    )


@transaction.atomic
def save_event(*, user, event: Event):
    """Bookmark an event. Database uniqueness is the final duplicate guard (§10.2)."""
    saved, created = SavedEvent.objects.get_or_create(user=user, event=event)
    return saved, created


@transaction.atomic
def unsave_event(*, user, event: Event) -> bool:
    deleted, _ = SavedEvent.objects.filter(user=user, event=event).delete()
    return bool(deleted)

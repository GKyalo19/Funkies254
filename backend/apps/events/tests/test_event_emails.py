"""Transactional email: event registration confirmations and preference matches."""

import pytest
from django.core import mail

from apps.events.models import Event
from apps.events.services import notify_users_of_matching_event, set_event_verified
from apps.preferences.models import UserPreferenceCategory

pytestmark = pytest.mark.django_db


def test_registering_for_an_event_sends_confirmation(api, student, event, login):
    login(student)
    response = api.post("/api/registrations/", {"event_id": str(event.id)}, format="json")

    assert response.status_code == 201, response.data
    assert len(mail.outbox) == 1
    assert student.email in mail.outbox[0].to
    assert event.title in mail.outbox[0].subject


def test_duplicate_registration_does_not_send_another_email(api, student, event, login):
    login(student)
    api.post("/api/registrations/", {"event_id": str(event.id)}, format="json")
    mail.outbox.clear()

    response = api.post("/api/registrations/", {"event_id": str(event.id)}, format="json")

    assert response.status_code == 409
    assert mail.outbox == []


def test_verifying_an_event_emails_students_with_matching_preferences(
    student, event, admin_user, categories, school_levels
):
    preference = student.preference
    preference.school_level = event.school_level
    preference.email_notifications = True
    preference.save()
    UserPreferenceCategory.objects.get_or_create(
        user_preference=preference, category=categories["math"]
    )

    Event.objects.filter(pk=event.pk).update(is_verified=False)
    event.refresh_from_db()
    mail.outbox.clear()

    set_event_verified(actor=admin_user, event=event, verified=True)

    assert len(mail.outbox) == 1
    assert student.email in mail.outbox[0].to
    assert event.title in mail.outbox[0].subject


def test_preference_mismatch_does_not_send_match_email(
    student, event, admin_user, categories
):
    preference = student.preference
    preference.email_notifications = True
    preference.save()
    UserPreferenceCategory.objects.get_or_create(
        user_preference=preference, category=categories["sports"]
    )
    Event.objects.filter(pk=event.pk).update(is_verified=False)
    event.refresh_from_db()
    mail.outbox.clear()

    set_event_verified(actor=admin_user, event=event, verified=True)

    assert mail.outbox == []


def test_email_notifications_opt_out_skips_match_email(
    student, event, admin_user, categories
):
    preference = student.preference
    preference.email_notifications = False
    preference.save()
    UserPreferenceCategory.objects.get_or_create(
        user_preference=preference, category=categories["math"]
    )

    assert notify_users_of_matching_event(event) == 0
    assert mail.outbox == []

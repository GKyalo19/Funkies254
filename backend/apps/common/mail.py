"""
Transactional email helpers.

All outgoing mail goes through Django's email backend, which is Mailtrap SMTP
when EMAIL_HOST is configured and the console backend otherwise. Send failures
are logged and swallowed so a downed mail provider never rolls back a
successful user-facing write.
"""

import logging

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string

logger = logging.getLogger(__name__)


def event_page_url(event) -> str:
    base = (settings.FRONTEND_BASE_URL or "").rstrip("/")
    return f"{base}/pages/event.html?slug={event.slug}"


def send_templated_email(*, to, subject, template, context) -> bool:
    """Render ``emails/<template>.txt`` + ``.html`` and send. Returns success."""
    recipient = [to] if isinstance(to, str) else list(to)
    if not recipient:
        return False

    payload = {
        "frontend_base_url": (settings.FRONTEND_BASE_URL or "").rstrip("/"),
        **context,
    }
    text_body = render_to_string(f"emails/{template}.txt", payload)
    html_body = render_to_string(f"emails/{template}.html", payload)

    message = EmailMultiAlternatives(
        subject=subject,
        body=text_body,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=recipient,
    )
    message.attach_alternative(html_body, "text/html")

    try:
        message.send()
        return True
    except Exception:
        logger.exception("Failed to send '%s' to %s", subject, recipient)
        return False


def send_verification_code_email(user, code: str) -> bool:
    ttl = settings.EMAIL_VERIFICATION_CODE_TTL_MINUTES
    return send_templated_email(
        to=user.email,
        subject="Your Funkies254 verification code",
        template="verification_code",
        context={"user": user, "code": code, "ttl_minutes": ttl},
    )


def send_registration_confirmation_email(user, event) -> bool:
    return send_templated_email(
        to=user.email,
        subject=f"You're registered: {event.title}",
        template="event_registration",
        context={
            "user": user,
            "event": event,
            "event_url": event_page_url(event),
            "where": _event_place(event),
        },
    )


def send_new_event_match_email(user, event) -> bool:
    return send_templated_email(
        to=user.email,
        subject=f"New event for you: {event.title}",
        template="event_match",
        context={
            "user": user,
            "event": event,
            "event_url": event_page_url(event),
            "where": _event_place(event),
        },
    )


def _event_place(event) -> str:
    if event.is_virtual:
        return "Virtual event"
    parts = [part for part in (event.venue, event.location) if part]
    return " · ".join(parts) or "Venue to be confirmed"

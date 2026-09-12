"""
Transactional email helpers.

All outgoing mail goes through the Mailtrap Email API over HTTPS.
Send failures are logged and swallowed so a downed mail provider never
rolls back a successful user-facing write.
"""

import logging
from email.utils import parseaddr

import requests
from django.conf import settings
from django.template.loader import render_to_string

logger = logging.getLogger(__name__)

MAILTRAP_API_URL = "https://send.api.mailtrap.io/api/send"


def event_page_url(event) -> str:
    base = (settings.FRONTEND_BASE_URL or "").rstrip("/")
    return f"{base}/pages/event.html?slug={event.slug}"


def send_templated_email(*, to, subject, template, context) -> bool:
    """Render ``emails/<template>.txt`` + ``.html`` and send via Mailtrap API."""

    recipient = [to] if isinstance(to, str) else list(to)
    if not recipient:
        return False

    api_token = getattr(settings, "MAILTRAP_API_TOKEN", "")
    if not api_token:
        logger.error("MAILTRAP_API_TOKEN is not configured")
        return False

    payload = {
        "frontend_base_url": (settings.FRONTEND_BASE_URL or "").rstrip("/"),
        **context,
    }

    text_body = render_to_string(f"emails/{template}.txt", payload)
    html_body = render_to_string(f"emails/{template}.html", payload)

    sender_name, sender_email = parseaddr(settings.DEFAULT_FROM_EMAIL)

    if not sender_email:
        logger.error("DEFAULT_FROM_EMAIL does not contain a valid email address")
        return False

    mail_data = {
        "from": {
            "email": sender_email,
            "name": sender_name or "Funkies254",
        },
        "to": [{"email": email} for email in recipient],
        "subject": subject,
        "text": text_body,
        "html": html_body,
    }

    try:
        response = requests.post(
            MAILTRAP_API_URL,
            headers={
                "Authorization": f"Bearer {api_token}",
                "Content-Type": "application/json",
            },
            json=mail_data,
            timeout=15,
        )

        response.raise_for_status()

        logger.info(
            "Email sent successfully via Mailtrap API: '%s' to %s",
            subject,
            recipient,
        )
        return True

    except requests.RequestException:
        logger.exception(
            "Failed to send '%s' to %s via Mailtrap API",
            subject,
            recipient,
        )
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
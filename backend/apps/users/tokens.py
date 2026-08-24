"""
Token issuing and cookie transport (§8.1, §8.2).

Tokens are never placed in a response body — they only travel as httpOnly
cookies, so frontend JavaScript can never read them.
"""

import logging

from django.conf import settings
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken

logger = logging.getLogger(__name__)


def issue_tokens(user):
    """Return a fresh (refresh, access) pair for ``user``."""
    refresh = RefreshToken.for_user(user)
    return refresh, refresh.access_token


def _cookie_kwargs():
    return {
        "httponly": True,
        "secure": settings.JWT_COOKIE_SECURE,
        "samesite": settings.JWT_COOKIE_SAMESITE,
        "domain": settings.JWT_COOKIE_DOMAIN,
    }


def set_auth_cookies(response, access_token, refresh_token=None):
    lifetimes = settings.SIMPLE_JWT
    response.set_cookie(
        settings.JWT_ACCESS_COOKIE_NAME,
        str(access_token),
        max_age=int(lifetimes["ACCESS_TOKEN_LIFETIME"].total_seconds()),
        path=settings.JWT_ACCESS_COOKIE_PATH,
        **_cookie_kwargs(),
    )
    if refresh_token is not None:
        response.set_cookie(
            settings.JWT_REFRESH_COOKIE_NAME,
            str(refresh_token),
            max_age=int(lifetimes["REFRESH_TOKEN_LIFETIME"].total_seconds()),
            path=settings.JWT_REFRESH_COOKIE_PATH,
            **_cookie_kwargs(),
        )
    return response


def clear_auth_cookies(response):
    for name, path in (
        (settings.JWT_ACCESS_COOKIE_NAME, settings.JWT_ACCESS_COOKIE_PATH),
        (settings.JWT_REFRESH_COOKIE_NAME, settings.JWT_REFRESH_COOKIE_PATH),
    ):
        response.delete_cookie(
            name,
            path=path,
            domain=settings.JWT_COOKIE_DOMAIN,
            samesite=settings.JWT_COOKIE_SAMESITE,
        )
    return response


def blacklist_refresh_token(raw_refresh_token) -> bool:
    """Best-effort blacklisting; an already-invalid token is not an error."""
    if not raw_refresh_token:
        return False
    try:
        RefreshToken(raw_refresh_token).blacklist()
    except (TokenError, AttributeError) as exc:
        logger.info("Refresh token could not be blacklisted: %s", exc)
        return False
    return True


def read_refresh_token(request):
    """Refresh tokens are read from the cookie first, then the request body."""
    return request.COOKIES.get(settings.JWT_REFRESH_COOKIE_NAME) or (
        request.data.get("refresh") if hasattr(request, "data") else None
    )

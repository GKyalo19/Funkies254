"""
Cookie-based JWT authentication.

`djangorestframework-simplejwt` normally expects the access token in an
`Authorization: Bearer <token>` header. We instead store it in an httpOnly
cookie so client-side JavaScript can never read or exfiltrate the token
(XSS protection) — the browser attaches it automatically on every request.

This class only overrides *where the token is read from*; everything else
(signature/expiry validation, building the `request.user`) is inherited
from SimpleJWT's `JWTAuthentication`.
"""
from django.conf import settings
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import InvalidToken


class CookieJWTAuthentication(JWTAuthentication):
    def authenticate(self, request):
        raw_token = request.COOKIES.get(settings.ACCESS_TOKEN_COOKIE)
        if raw_token is None:
            return None

        try:
            validated_token = self.get_validated_token(raw_token)
        except InvalidToken:
            return None

        return self.get_user(validated_token), validated_token


def set_auth_cookies(response, access_token, refresh_token):
    """Attach both tokens as httpOnly cookies on an outgoing response."""
    access_lifetime = settings.SIMPLE_JWT["ACCESS_TOKEN_LIFETIME"]
    refresh_lifetime = settings.SIMPLE_JWT["REFRESH_TOKEN_LIFETIME"]

    common_kwargs = dict(
        httponly=True,
        secure=settings.JWT_COOKIE_SECURE,
        samesite=settings.JWT_COOKIE_SAMESITE,
        path="/",
    )
    response.set_cookie(
        settings.ACCESS_TOKEN_COOKIE, str(access_token), max_age=int(access_lifetime.total_seconds()), **common_kwargs
    )
    response.set_cookie(
        settings.REFRESH_TOKEN_COOKIE, str(refresh_token), max_age=int(refresh_lifetime.total_seconds()), **common_kwargs
    )


def clear_auth_cookies(response):
    response.delete_cookie(settings.ACCESS_TOKEN_COOKIE, path="/")
    response.delete_cookie(settings.REFRESH_TOKEN_COOKIE, path="/")

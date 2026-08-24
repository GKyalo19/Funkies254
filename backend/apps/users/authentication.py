"""
Cookie-transported JWT authentication (§8.1).

The access token normally arrives in an httpOnly cookie. An Authorization
header is still accepted, which keeps server-to-server calls and quick manual
testing possible. When the credential came from a cookie, unsafe requests are
subject to CSRF verification, because cookies are attached by the browser
automatically.
"""

from django.conf import settings
from django.middleware.csrf import CsrfViewMiddleware
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import SAFE_METHODS
from rest_framework_simplejwt.authentication import JWTAuthentication


class _CSRFCheck(CsrfViewMiddleware):
    def _reject(self, request, reason):
        return reason


class CookieJWTAuthentication(JWTAuthentication):
    def authenticate(self, request):
        raw_token = None
        came_from_cookie = False

        header = self.get_header(request)
        if header is not None:
            raw_token = self.get_raw_token(header)

        if raw_token is None:
            raw_token = request.COOKIES.get(settings.JWT_ACCESS_COOKIE_NAME)
            came_from_cookie = raw_token is not None

        if not raw_token:
            return None

        validated_token = self.get_validated_token(raw_token)
        user = self.get_user(validated_token)

        if came_from_cookie and request.method not in SAFE_METHODS:
            self.enforce_csrf(request)

        return user, validated_token

    def enforce_csrf(self, request):
        if not settings.JWT_COOKIE_CSRF_ENFORCED:
            return
        check = _CSRFCheck(lambda _request: None)
        check.process_request(request)
        reason = check.process_view(request, None, (), {})
        if reason:
            raise PermissionDenied(f"CSRF verification failed: {reason}")

"""
Domain exceptions and one consistent JSON error envelope.

Every error response has the shape::

    {"detail": "...", "code": "...", "errors": {...}}

``errors`` is present only for field validation failures, so the frontend can
render inline messages without special-casing each endpoint.
"""

import logging

from django.core.exceptions import PermissionDenied as DjangoPermissionDenied
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import IntegrityError
from django.http import Http404
from rest_framework import status
from rest_framework.exceptions import APIException
from rest_framework.response import Response
from rest_framework.views import exception_handler as drf_exception_handler

logger = logging.getLogger(__name__)


class AuthenticationError(APIException):
    """
    Credentials were rejected.

    DRF downgrades ``AuthenticationFailed`` to 403 on views that declare no
    authenticator (such as login), so login failures use this class to stay a
    truthful 401.
    """

    status_code = status.HTTP_401_UNAUTHORIZED
    default_detail = "Authentication failed."
    default_code = "authentication_failed"


class ConflictError(APIException):
    """The request collides with existing state (duplicate save, etc.)."""

    status_code = status.HTTP_409_CONFLICT
    default_detail = "This action conflicts with the current state of the resource."
    default_code = "conflict"


class BusinessRuleError(APIException):
    """A domain rule rejected an otherwise well-formed request."""

    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = "This action is not allowed."
    default_code = "business_rule_violation"


class StorageError(APIException):
    status_code = status.HTTP_502_BAD_GATEWAY
    default_detail = "Media storage is unavailable. Please try again."
    default_code = "storage_error"


def api_exception_handler(exc, context):
    if isinstance(exc, DjangoValidationError):
        exc = _as_drf_validation_error(exc)
    elif isinstance(exc, DjangoPermissionDenied):
        from rest_framework.exceptions import PermissionDenied

        exc = PermissionDenied()
    elif isinstance(exc, IntegrityError):
        logger.warning("Database integrity error: %s", exc)
        exc = ConflictError("This record already exists or violates a database rule.")

    response = drf_exception_handler(exc, context)

    if response is None:
        return None

    return Response(_envelope(exc, response), status=response.status_code, headers=_headers(response))


def _as_drf_validation_error(exc):
    from rest_framework.exceptions import ValidationError

    if hasattr(exc, "message_dict"):
        return ValidationError(exc.message_dict)
    return ValidationError(exc.messages)


def _headers(response):
    return {
        key: value
        for key, value in response.items()
        if key.lower() in {"www-authenticate", "retry-after"}
    }


def _envelope(exc, response):
    data = response.data
    code = _code(exc, data)

    if isinstance(data, dict) and "detail" in data and len(data) == 1:
        return {"detail": str(data["detail"]), "code": code}

    if isinstance(data, dict):
        detail = _first_message(data) or "The submitted data was invalid."
        return {"detail": detail, "code": code, "errors": data}

    if isinstance(data, list):
        return {"detail": _flatten(data), "code": code, "errors": {"non_field_errors": data}}

    return {"detail": str(data), "code": code}


def _code(exc, data):
    """Prefer the code carried by the raised detail over the class default."""
    detail = data.get("detail") if isinstance(data, dict) else None
    return getattr(detail, "code", None) or getattr(exc, "default_code", "error")


def _first_message(data):
    for field, value in data.items():
        message = _flatten(value)
        if not message:
            continue
        if field in {"detail", "non_field_errors"}:
            return message
        return f"{field}: {message}"
    return None


def _flatten(value):
    if isinstance(value, (list, tuple)):
        return " ".join(_flatten(item) for item in value if item)
    if isinstance(value, dict):
        return " ".join(_flatten(item) for item in value.values() if item)
    return str(value)


def not_found_response(message="Not found."):
    raise Http404(message)

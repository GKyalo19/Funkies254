"""
Supabase Storage client (§11).

PostgreSQL stores URLs only; the binary objects live in Supabase Storage. The
service-role credential is used exclusively here, on the backend, and is never
sent to the frontend.
"""

import logging
import mimetypes
import uuid
from urllib.parse import quote

import requests
from django.conf import settings
from rest_framework import status

from apps.common.exceptions import StorageError

logger = logging.getLogger(__name__)

EVENT_COVERS = "event-covers"
AVATARS = "avatars"

_BUCKETS = {
    EVENT_COVERS: lambda: settings.SUPABASE_BUCKET_EVENT_COVERS,
    AVATARS: lambda: settings.SUPABASE_BUCKET_AVATARS,
}


class UploadValidationError(StorageError):
    status_code = status.HTTP_400_BAD_REQUEST
    default_code = "invalid_upload"


def is_configured() -> bool:
    return bool(settings.SUPABASE_URL and settings.SUPABASE_SERVICE_ROLE_KEY)


def validate_image(upload) -> None:
    """Validate content type and size before spending a network round trip."""
    content_type = (getattr(upload, "content_type", "") or "").lower()
    allowed = [item.lower() for item in settings.UPLOAD_ALLOWED_IMAGE_TYPES]
    if content_type not in allowed:
        raise UploadValidationError(
            f"Unsupported file type '{content_type or 'unknown'}'. "
            f"Allowed types: {', '.join(allowed)}."
        )

    size = getattr(upload, "size", None)
    if size is not None and size > settings.UPLOAD_MAX_BYTES:
        limit_mb = settings.UPLOAD_MAX_BYTES / (1024 * 1024)
        raise UploadValidationError(f"File is larger than the {limit_mb:.1f} MB limit.")


def build_object_path(prefix: str, upload, owner_id=None) -> str:
    """Object paths are always generated server-side, never client-supplied."""
    extension = mimetypes.guess_extension(getattr(upload, "content_type", "") or "") or ""
    if extension == ".jpe":
        extension = ".jpg"
    parts = [part for part in (prefix, str(owner_id) if owner_id else None) if part]
    parts.append(f"{uuid.uuid4().hex}{extension}")
    return "/".join(parts)


def _bucket_name(bucket: str) -> str:
    resolver = _BUCKETS.get(bucket)
    return resolver() if resolver else bucket


def _headers() -> dict:
    return {"Authorization": f"Bearer {settings.SUPABASE_SERVICE_ROLE_KEY}"}


def _require_configuration() -> None:
    if not is_configured():
        raise StorageError(
            "Supabase Storage is not configured. Set SUPABASE_URL and "
            "SUPABASE_SERVICE_ROLE_KEY."
        )


def public_url(bucket: str, path: str) -> str:
    base = settings.SUPABASE_URL.rstrip("/")
    return f"{base}/storage/v1/object/public/{_bucket_name(bucket)}/{quote(path)}"


def upload(bucket: str, path: str, upload_file, *, content_type=None) -> str:
    """Upload one object and return its public URL."""
    _require_configuration()
    base = settings.SUPABASE_URL.rstrip("/")
    endpoint = f"{base}/storage/v1/object/{_bucket_name(bucket)}/{quote(path)}"
    upload_file.seek(0)

    try:
        response = requests.post(
            endpoint,
            data=upload_file.read(),
            headers={
                **_headers(),
                "Content-Type": content_type
                or getattr(upload_file, "content_type", "application/octet-stream"),
                "x-upsert": "true",
                "cache-control": "3600",
            },
            timeout=settings.SUPABASE_STORAGE_TIMEOUT,
        )
    except requests.RequestException as exc:
        logger.exception("Supabase Storage upload failed")
        raise StorageError("Could not reach media storage.") from exc

    if response.status_code >= 400:
        logger.error("Supabase Storage upload rejected: %s %s", response.status_code, response.text)
        raise StorageError("Media storage rejected the upload.")

    return public_url(bucket, path)


def delete(bucket: str, path: str) -> bool:
    """Delete one object. Missing objects are treated as already deleted."""
    _require_configuration()
    base = settings.SUPABASE_URL.rstrip("/")
    endpoint = f"{base}/storage/v1/object/{_bucket_name(bucket)}/{quote(path)}"

    try:
        response = requests.delete(
            endpoint, headers=_headers(), timeout=settings.SUPABASE_STORAGE_TIMEOUT
        )
    except requests.RequestException as exc:
        logger.exception("Supabase Storage delete failed")
        raise StorageError("Could not reach media storage.") from exc

    return response.status_code < 400 or response.status_code == 404


def path_from_url(bucket: str, url: str):
    """Recover the object path from a stored public URL, or None if foreign."""
    if not url:
        return None
    marker = f"/storage/v1/object/public/{_bucket_name(bucket)}/"
    if marker not in url:
        return None
    return url.split(marker, 1)[1]


def replace(bucket: str, previous_url, path: str, upload_file, *, content_type=None) -> str:
    """Upload a replacement object and remove the one it supersedes."""
    new_url = upload(bucket, path, upload_file, content_type=content_type)
    previous_path = path_from_url(bucket, previous_url)
    if previous_path and previous_path != path:
        try:
            delete(bucket, previous_path)
        except StorageError:
            logger.warning("Could not delete superseded object %s/%s", bucket, previous_path)
    return new_url


def upload_event_cover(upload_file, event_id=None) -> str:
    validate_image(upload_file)
    path = build_object_path("events", upload_file, event_id)
    return upload(EVENT_COVERS, path, upload_file)


def upload_avatar(upload_file, user_id) -> str:
    validate_image(upload_file)
    path = build_object_path("users", upload_file, user_id)
    return upload(AVATARS, path, upload_file)

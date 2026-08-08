"""
Thin wrapper around Supabase Storage's REST API.

We talk to Supabase over plain HTTP (via `requests`) instead of the
`supabase-py` SDK to keep the dependency list small — uploading/deleting a
file is just two REST calls. This is the only place in the codebase that
knows about Supabase Storage's URL shape, so swapping providers later
(e.g. moving large video files to Cloudinary) only means editing this file.
"""
import mimetypes
import uuid

import requests
from django.conf import settings


class SupabaseStorageError(Exception):
    """Raised when Supabase Storage returns a non-2xx response."""


def _object_endpoint(path: str) -> str:
    bucket = settings.SUPABASE_STORAGE_BUCKET
    return f"{settings.SUPABASE_URL}/storage/v1/object/{bucket}/{path}"


def _public_url(path: str) -> str:
    bucket = settings.SUPABASE_STORAGE_BUCKET
    return f"{settings.SUPABASE_URL}/storage/v1/object/public/{bucket}/{path}"


def upload_file(file_obj, folder: str) -> str:
    """
    Upload a Django `UploadedFile` to Supabase Storage and return its public URL.

    `folder` groups files logically inside the bucket, e.g. "events/covers"
    or "users/avatars". A random filename avoids collisions and avoids
    leaking the original filename.
    """
    if not settings.SUPABASE_URL or not settings.SUPABASE_SERVICE_ROLE_KEY:
        raise SupabaseStorageError(
            "Supabase Storage is not configured. Set SUPABASE_URL and "
            "SUPABASE_SERVICE_ROLE_KEY in backend/.env."
        )

    extension = ""
    if "." in getattr(file_obj, "name", ""):
        extension = "." + file_obj.name.rsplit(".", 1)[-1].lower()
    path = f"{folder}/{uuid.uuid4().hex}{extension}"

    content_type = getattr(file_obj, "content_type", None) or mimetypes.guess_type(file_obj.name)[0] or "application/octet-stream"

    response = requests.post(
        _object_endpoint(path),
        headers={
            "Authorization": f"Bearer {settings.SUPABASE_SERVICE_ROLE_KEY}",
            "Content-Type": content_type,
            "x-upsert": "true",
        },
        data=file_obj.read(),
        timeout=30,
    )
    if response.status_code not in (200, 201):
        raise SupabaseStorageError(f"Supabase upload failed ({response.status_code}): {response.text}")

    return _public_url(path)


def delete_file(public_url: str) -> None:
    """Best-effort delete of a previously uploaded file, given its public URL."""
    if not public_url or "/storage/v1/object/public/" not in public_url:
        return
    bucket = settings.SUPABASE_STORAGE_BUCKET
    path = public_url.split(f"/storage/v1/object/public/{bucket}/", 1)[-1]

    requests.delete(
        _object_endpoint(path),
        headers={"Authorization": f"Bearer {settings.SUPABASE_SERVICE_ROLE_KEY}"},
        timeout=15,
    )

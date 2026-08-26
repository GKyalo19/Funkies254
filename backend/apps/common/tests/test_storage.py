"""Supabase Storage tests (§15: valid/invalid files, upload, replacement/deletion)."""

import io

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile

from apps.common import supabase_storage
from apps.common.exceptions import StorageError

pytestmark = pytest.mark.django_db


@pytest.fixture
def storage_settings(settings):
    settings.SUPABASE_URL = "https://project.supabase.co"
    settings.SUPABASE_SERVICE_ROLE_KEY = "service-role-key"
    settings.SUPABASE_BUCKET_EVENT_COVERS = "event-covers"
    settings.SUPABASE_BUCKET_AVATARS = "avatars"
    settings.UPLOAD_MAX_BYTES = 1024
    settings.UPLOAD_ALLOWED_IMAGE_TYPES = ["image/jpeg", "image/png"]
    return settings


def png(size=100, name="cover.png", content_type="image/png"):
    return SimpleUploadedFile(name, b"x" * size, content_type=content_type)


class FakeResponse:
    def __init__(self, status_code=200, text=""):
        self.status_code = status_code
        self.text = text


def test_valid_image_passes_validation(storage_settings):
    supabase_storage.validate_image(
        SimpleUploadedFile("cover.png", _one_pixel_png(), content_type="image/png")
    )


def test_unsupported_content_type_is_rejected(storage_settings):
    with pytest.raises(StorageError) as exc:
        supabase_storage.validate_image(png(content_type="application/pdf"))

    assert exc.value.status_code == 400


def test_oversized_file_is_rejected(storage_settings):
    with pytest.raises(StorageError) as exc:
        supabase_storage.validate_image(png(size=2048))

    assert "larger than" in str(exc.value.detail)


def test_object_path_is_generated_server_side(storage_settings):
    path = supabase_storage.build_object_path("events", png(name="../../etc/passwd.png"))

    assert path.startswith("events/")
    assert ".." not in path
    assert path.endswith(".png")


def test_upload_returns_public_url(storage_settings, monkeypatch):
    captured = {}

    def fake_post(url, data=None, headers=None, timeout=None):
        captured["url"] = url
        captured["headers"] = headers
        return FakeResponse(200)

    monkeypatch.setattr(supabase_storage.requests, "post", fake_post)

    url = supabase_storage.upload("event-covers", "events/abc.png", png())

    assert url == "https://project.supabase.co/storage/v1/object/public/event-covers/events/abc.png"
    assert captured["headers"]["Authorization"] == "Bearer service-role-key"
    assert "/storage/v1/object/event-covers/" in captured["url"]


def test_upload_failure_raises_storage_error(storage_settings, monkeypatch):
    monkeypatch.setattr(
        supabase_storage.requests,
        "post",
        lambda *args, **kwargs: FakeResponse(403, "forbidden"),
    )

    with pytest.raises(StorageError):
        supabase_storage.upload("event-covers", "events/abc.png", png())


def test_replace_deletes_the_superseded_object(storage_settings, monkeypatch):
    deleted = []
    monkeypatch.setattr(
        supabase_storage.requests, "post", lambda *args, **kwargs: FakeResponse(200)
    )
    monkeypatch.setattr(
        supabase_storage.requests,
        "delete",
        lambda url, **kwargs: deleted.append(url) or FakeResponse(200),
    )

    previous = supabase_storage.public_url("event-covers", "events/old.png")
    supabase_storage.replace("event-covers", previous, "events/new.png", png())

    assert deleted and deleted[0].endswith("/storage/v1/object/event-covers/events/old.png")


def test_path_from_url_ignores_foreign_urls(storage_settings):
    own = supabase_storage.public_url("avatars", "users/1/a.png")

    assert supabase_storage.path_from_url("avatars", own) == "users/1/a.png"
    assert supabase_storage.path_from_url("avatars", "https://example.com/a.png") is None


def test_upload_without_configuration_raises(settings):
    settings.SUPABASE_URL = ""
    settings.SUPABASE_SERVICE_ROLE_KEY = ""

    assert supabase_storage.is_configured() is False
    with pytest.raises(StorageError):
        supabase_storage.upload("event-covers", "events/a.png", png())


def test_avatar_upload_helper_uses_avatars_bucket(storage_settings, monkeypatch):
    urls = []
    monkeypatch.setattr(
        supabase_storage.requests,
        "post",
        lambda url, **kwargs: urls.append(url) or FakeResponse(200),
    )

    result = supabase_storage.upload_avatar(
        SimpleUploadedFile("avatar.png", _one_pixel_png(), content_type="image/png"),
        "user-1",
    )

    assert "/object/avatars/avatars/user-1/" in urls[0]
    assert "/object/public/avatars/" in result


def test_event_cover_upload_through_the_api(
    api, staff, event_payload, storage_settings, monkeypatch, login
):
    monkeypatch.setattr(
        supabase_storage.requests, "post", lambda *args, **kwargs: FakeResponse(200)
    )
    login(staff)

    payload = {**event_payload, "category_ids": event_payload["category_ids"]}
    payload["cover_image"] = SimpleUploadedFile(
        "cover.png", _one_pixel_png(), content_type="image/png"
    )

    response = api.post("/api/events/", payload, format="multipart")

    assert response.status_code == 201, response.data
    assert response.data["cover_image_url"].startswith(
        "https://project.supabase.co/storage/v1/object/public/event-covers/"
    )


def test_invalid_cover_image_is_rejected_by_the_api(
    api, staff, event_payload, storage_settings, login
):
    login(staff)
    payload = {**event_payload}
    payload["cover_image"] = SimpleUploadedFile(
        "notes.pdf", b"%PDF-1.4", content_type="application/pdf"
    )

    response = api.post("/api/events/", payload, format="multipart")

    assert response.status_code == 400


def _one_pixel_png():
    from PIL import Image

    buffer = io.BytesIO()
    Image.new("RGB", (1, 1), color="white").save(buffer, format="PNG")
    return buffer.getvalue()

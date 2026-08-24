"""Institution model (§4.2) — the organizer that hosts events."""

from django.conf import settings
from django.db import models
from django.utils.text import slugify

from apps.common.models import TimeStampedModel, UUIDPrimaryKeyModel


class Institution(UUIDPrimaryKeyModel, TimeStampedModel):
    name = models.CharField(max_length=200)
    email = models.EmailField(null=True, blank=True)
    phone = models.CharField(max_length=32, null=True, blank=True)
    slug = models.SlugField(max_length=220, unique=True)
    logo_url = models.TextField(
        null=True, blank=True, help_text="Supabase Storage URL for the logo."
    )
    location = models.TextField(null=True, blank=True)
    website = models.URLField(null=True, blank=True)
    verified = models.BooleanField(
        default=False, help_text="Set by an administrator after review."
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="institutions_created",
        db_column="created_by",
    )

    class Meta:
        db_table = "institutions"
        ordering = ("name",)
        indexes = [
            models.Index(fields=["slug"], name="institutions_slug_idx"),
            models.Index(fields=["verified"], name="institutions_verified_idx"),
        ]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = self.generate_unique_slug(self.name)
        super().save(*args, **kwargs)

    @classmethod
    def generate_unique_slug(cls, value: str) -> str:
        base = slugify(value)[:200] or "institution"
        slug = base
        suffix = 2
        while cls.objects.filter(slug=slug).exists():
            slug = f"{base}-{suffix}"
            suffix += 1
        return slug

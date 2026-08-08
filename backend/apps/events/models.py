from django.conf import settings
from django.db import models
from django.utils import timezone
from django.utils.text import slugify

from apps.organizers.models import Organizer
from apps.users.models import EducationLevel


class Category(models.Model):
    """
    A single flat taxonomy shared by events, user preferences, and listing
    filters — covers both academic subjects (Math, Science, Literature) and
    activity types (Sports, Volleyball, Rugby) seen in the Figma designs.
    """

    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=120, unique=True, blank=True)
    icon = models.CharField(max_length=50, blank=True, help_text="Icon identifier used by the frontend, e.g. an iconify name.")

    class Meta:
        ordering = ["name"]
        verbose_name_plural = "categories"

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)


class EventStatus(models.TextChoices):
    DRAFT = "draft", "Draft"
    PUBLISHED = "published", "Published"
    CANCELLED = "cancelled", "Cancelled"


class Event(models.Model):
    """A single event listing — the core content of the whole platform."""

    title = models.CharField(max_length=255)
    slug = models.SlugField(max_length=280, unique=True, blank=True)
    organizer = models.ForeignKey(Organizer, on_delete=models.CASCADE, related_name="events")
    categories = models.ManyToManyField(Category, related_name="events", blank=True)

    short_description = models.CharField(
        max_length=255, blank=True, help_text="Shown on event cards. Falls back to a trimmed description."
    )
    description = models.TextField()

    education_level = models.CharField(
        max_length=20, choices=EducationLevel.choices, default=EducationLevel.BOTH,
        help_text="Who this event targets — used for both filtering and recommendations.",
    )

    venue_name = models.CharField(max_length=255)
    address = models.CharField(max_length=500, blank=True)
    location = models.CharField(max_length=120, help_text="City/region, e.g. 'Nairobi'. Used for the location filter.")

    start_datetime = models.DateTimeField()
    end_datetime = models.DateTimeField(null=True, blank=True)

    registration_fee = models.DecimalField(max_digits=10, decimal_places=2, default=0, help_text="0 means free.")
    capacity = models.PositiveIntegerField(null=True, blank=True, help_text="Leave blank for unlimited.")
    external_registration_url = models.URLField(
        blank=True, help_text="Optional — if set, 'Register' sends users here instead of registering in-platform."
    )

    cover_image_url = models.URLField(blank=True, help_text="Public Supabase Storage URL.")
    is_featured = models.BooleanField(default=False, help_text="Curator boost — featured events rank higher in the feed.")
    status = models.CharField(max_length=20, choices=EventStatus.choices, default=EventStatus.PUBLISHED)

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="events_created"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["start_datetime"]
        indexes = [
            models.Index(fields=["start_datetime"]),
            models.Index(fields=["location"]),
            models.Index(fields=["status"]),
        ]

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.title)
            slug = base_slug
            suffix = 1
            while Event.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                suffix += 1
                slug = f"{base_slug}-{suffix}"
            self.slug = slug
        super().save(*args, **kwargs)

    @property
    def is_free(self):
        return self.registration_fee == 0

    @property
    def is_past(self):
        return self.start_datetime < timezone.now()

    @property
    def registrations_count(self):
        return self.registrations.filter(status="registered").count()

    @property
    def spots_left(self):
        if self.capacity is None:
            return None
        return max(self.capacity - self.registrations_count, 0)

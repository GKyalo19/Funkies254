"""
Event domain models (§4.3 – §4.7).

Category and SchoolLevel are reference taxonomies stored as rows so the
taxonomy can evolve without a migration (§4.3, §18).
"""

from django.conf import settings
from django.db import models
from django.utils.text import slugify

from apps.common.models import TimeStampedModel, UUIDPrimaryKeyModel


class SchoolLevel(UUIDPrimaryKeyModel):
    name = models.CharField(max_length=100)
    slug = models.SlugField(max_length=120, unique=True)

    class Meta:
        db_table = "school_levels"
        ordering = ("name",)

    def __str__(self):
        return self.name


class Category(UUIDPrimaryKeyModel):
    name = models.CharField(max_length=100)
    slug = models.SlugField(max_length=120, unique=True)

    class Meta:
        db_table = "categories"
        verbose_name_plural = "categories"
        ordering = ("name",)

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)


class EventQuerySet(models.QuerySet):
    def with_related(self):
        return self.select_related("institution", "school_level", "created_by").prefetch_related(
            "categories"
        )

    def verified(self):
        return self.filter(is_verified=True)

    def upcoming(self):
        from django.utils import timezone

        return self.filter(end_time__gte=timezone.now())

    def visible_to(self, user):
        """
        Curation visibility.

        Anonymous visitors and students see verified events only. Institution
        staff additionally see their own institution's drafts, and admins see
        everything.
        """
        from apps.common.enums import UserRole

        if not user or not user.is_authenticated:
            return self.verified()
        role = getattr(user, "role", None)
        if role in (UserRole.ADMIN, UserRole.SUPER_ADMIN):
            return self
        if role == UserRole.INSTITUTION_STAFF:
            own = models.Q(created_by=user)
            if user.institution_id:
                own |= models.Q(institution_id=user.institution_id)
            return self.filter(models.Q(is_verified=True) | own)
        return self.verified()


class Event(UUIDPrimaryKeyModel, TimeStampedModel):
    """
    Curated student event.

    Students never create events; only institution staff and admins do (§1.1).
    """

    title = models.CharField(max_length=250)
    slug = models.SlugField(
        max_length=280,
        unique=True,
        help_text="URL identifier used by GET /api/events/{slug}/.",
    )
    description = models.TextField()
    institution = models.ForeignKey(
        "organizers.Institution",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="events",
        db_column="institution_id",
    )
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()
    venue = models.CharField(max_length=250, null=True, blank=True)
    location = models.TextField(null=True, blank=True)
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    school_level = models.ForeignKey(
        SchoolLevel,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="events",
        db_column="school_level_id",
    )
    categories = models.ManyToManyField(
        Category, through="EventCategory", related_name="events", blank=True
    )
    cover_image_url = models.TextField(
        null=True, blank=True, help_text="Supabase Storage URL for the cover image."
    )
    registration_link = models.URLField(max_length=500, null=True, blank=True)
    is_verified = models.BooleanField(default=False)
    verified_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="events_verified",
        db_column="verified_by",
    )
    verified_at = models.DateTimeField(null=True, blank=True)
    is_virtual = models.BooleanField(default=False)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="events_created",
        db_column="created_by",
    )

    objects = EventQuerySet.as_manager()

    class Meta:
        db_table = "events"
        ordering = ("start_time",)
        indexes = [
            models.Index(fields=["start_time"], name="events_start_time_idx"),
            models.Index(fields=["end_time"], name="events_end_time_idx"),
            models.Index(fields=["is_verified"], name="events_is_verified_idx"),
            models.Index(fields=["institution"], name="events_institution_idx"),
            models.Index(fields=["school_level"], name="events_school_level_idx"),
        ]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(end_time__gt=models.F("start_time")),
                name="event_end_time_after_start_time",
            ),
            models.CheckConstraint(
                condition=models.Q(latitude__isnull=True)
                | models.Q(latitude__gte=-90, latitude__lte=90),
                name="event_latitude_in_range",
            ),
            models.CheckConstraint(
                condition=models.Q(longitude__isnull=True)
                | models.Q(longitude__gte=-180, longitude__lte=180),
                name="event_longitude_in_range",
            ),
        ]

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = self.generate_unique_slug(self.title)
        super().save(*args, **kwargs)

    @classmethod
    def generate_unique_slug(cls, value: str) -> str:
        base = slugify(value)[:250] or "event"
        slug = base
        suffix = 2
        while cls.objects.filter(slug=slug).exists():
            slug = f"{base}-{suffix}"
            suffix += 1
        return slug


class EventCategory(UUIDPrimaryKeyModel):
    """Explicit through table for Event ↔ Category (§4.6)."""

    event = models.ForeignKey(
        Event, on_delete=models.CASCADE, related_name="event_categories", db_column="event_id"
    )
    category = models.ForeignKey(
        Category,
        on_delete=models.CASCADE,
        related_name="event_categories",
        db_column="category_id",
    )

    class Meta:
        db_table = "event_categories"
        verbose_name_plural = "event categories"
        constraints = [
            models.UniqueConstraint(
                fields=("event", "category"), name="unique_event_category"
            )
        ]
        indexes = [
            models.Index(fields=["event"], name="event_category_event_idx"),
            models.Index(fields=["category"], name="event_category_cat_idx"),
        ]

    def __str__(self):
        return f"{self.event_id} · {self.category_id}"


class SavedEvent(UUIDPrimaryKeyModel):
    """A student's bookmark. Uniqueness is enforced by the database (§4.7)."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="saved_events",
        db_column="user_id",
    )
    event = models.ForeignKey(
        Event, on_delete=models.CASCADE, related_name="saved_by", db_column="event_id"
    )
    saved_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "saved_events"
        ordering = ("-saved_at",)
        constraints = [
            models.UniqueConstraint(fields=("user", "event"), name="unique_saved_event")
        ]
        indexes = [
            models.Index(fields=["user"], name="saved_event_user_idx"),
            models.Index(fields=["event"], name="saved_event_event_idx"),
        ]

    def __str__(self):
        return f"{self.user_id} saved {self.event_id}"

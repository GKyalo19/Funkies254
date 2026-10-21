"""User preferences (§4.9, §4.10) — exactly one record per user."""

from django.conf import settings
from django.db import models

from apps.common.enums import EventFormat
from apps.common.models import UUIDPrimaryKeyModel


def default_formats():
    return [choice.value for choice in EventFormat]


def default_days():
    return ["weekdays", "weekends"]


class UserPreference(UUIDPrimaryKeyModel):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="preference",
        db_column="user_id",
    )
    school_level = models.ForeignKey(
        "events.SchoolLevel",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="user_preferences",
        db_column="school_level_id",
    )
    email_notifications = models.BooleanField(default=True)
    push_notifications = models.BooleanField(default=False)
    sections = models.ManyToManyField(
        "events.Section",
        related_name="user_preferences",
        blank=True,
    )
    formats = models.JSONField(default=default_formats)
    country = models.CharField(max_length=100, default="Kenya")
    city = models.CharField(max_length=100, null=True, blank=True)
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    max_distance_km = models.PositiveIntegerField(null=True, blank=True)
    include_other_countries = models.BooleanField(default=False)
    free_only = models.BooleanField(default=False)
    days = models.JSONField(default=default_days)
    preferred_categories = models.ManyToManyField(
        "events.Category",
        through="UserPreferenceCategory",
        related_name="user_preferences",
        blank=True,
    )

    class Meta:
        db_table = "user_preferences"

    def __str__(self):
        return f"Preferences for {self.user_id}"


class UserPreferenceCategory(UUIDPrimaryKeyModel):
    """Explicit through table for UserPreference ↔ Category."""

    user_preference = models.ForeignKey(
        UserPreference,
        on_delete=models.CASCADE,
        related_name="category_links",
        db_column="user_preference_id",
    )
    category = models.ForeignKey(
        "events.Category",
        on_delete=models.CASCADE,
        related_name="preference_links",
        db_column="category_id",
    )

    class Meta:
        db_table = "user_preference_categories"
        verbose_name_plural = "user preference categories"
        constraints = [
            models.UniqueConstraint(
                fields=("user_preference", "category"),
                name="unique_user_preference_category",
            )
        ]
        indexes = [
            models.Index(fields=["user_preference"], name="pref_category_pref_idx"),
            models.Index(fields=["category"], name="pref_category_cat_idx"),
        ]

    def __str__(self):
        return f"{self.user_preference_id} · {self.category_id}"

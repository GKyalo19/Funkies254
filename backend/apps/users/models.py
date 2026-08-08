from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.db import models

from .managers import UserManager


class EducationLevel(models.TextChoices):
    """
    Shared with apps.preferences and apps.events — a student's own level and
    an event's target audience are compared using these same three values.
    """

    HIGH_SCHOOL = "high_school", "High School"
    COLLEGE = "college", "College"
    BOTH = "both", "High School & College"


class User(AbstractBaseUser, PermissionsMixin):
    """
    Custom user model, keyed by email instead of a separate username.

    `institution` captures the student's school/college (shown on the
    Register page in Figma) and later feeds into event recommendations
    (e.g. events hosted at or near the student's own school).
    """

    email = models.EmailField(unique=True)
    first_name = models.CharField(max_length=150, blank=True)
    last_name = models.CharField(max_length=150, blank=True)
    institution = models.CharField(
        max_length=255, blank=True, help_text="School/college the student is affiliated with."
    )
    education_level = models.CharField(
        max_length=20, choices=EducationLevel.choices, default=EducationLevel.HIGH_SCHOOL
    )
    phone_number = models.CharField(max_length=32, blank=True)
    avatar_url = models.URLField(blank=True, help_text="Public Supabase Storage URL.")

    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(
        default=False, help_text="Staff accounts can curate events/organizers via the admin."
    )
    date_joined = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = UserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    class Meta:
        ordering = ["-date_joined"]

    def __str__(self):
        return self.email

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}".strip() or self.email

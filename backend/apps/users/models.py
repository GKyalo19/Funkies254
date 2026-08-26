"""Custom user model (§4.1, §8)."""

from django.contrib.auth.base_user import AbstractBaseUser
from django.contrib.auth.models import PermissionsMixin
from django.db import models

from apps.common.enums import ADMIN_ROLES, UserRole
from apps.common.models import UUIDPrimaryKeyModel
from apps.users.managers import UserManager


class User(AbstractBaseUser, PermissionsMixin, UUIDPrimaryKeyModel):
    """
    Application user.

    The password hash comes from AbstractBaseUser; there is deliberately no
    plaintext password column (§4.1). ``role`` carries application semantics
    while ``is_staff``/``is_superuser`` carry Django admin semantics.
    """

    email = models.EmailField(unique=True, max_length=254)
    name = models.CharField(max_length=150)
    avatar_url = models.TextField(
        null=True, blank=True, help_text="Supabase Storage URL for the avatar."
    )
    role = models.CharField(
        max_length=32, choices=UserRole.choices, default=UserRole.STUDENT
    )
    institution = models.ForeignKey(
        "organizers.Institution",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="members",
        db_column="institution_id",
    )
    is_active = models.BooleanField(
        default=True, help_text="Inactive accounts cannot authenticate."
    )
    email_verified = models.BooleanField(
        default=False,
        help_text="Self-registered accounts must confirm a code emailed to them.",
    )
    email_verification_code_hash = models.CharField(max_length=64, blank=True, default="")
    email_verification_sent_at = models.DateTimeField(null=True, blank=True)
    email_verification_attempts = models.PositiveSmallIntegerField(default=0)
    is_staff = models.BooleanField(
        default=False, help_text="Grants access to the Django admin site."
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = UserManager()

    USERNAME_FIELD = "email"
    EMAIL_FIELD = "email"
    REQUIRED_FIELDS = ["name"]

    class Meta:
        db_table = "users"
        ordering = ("-created_at",)
        indexes = [
            models.Index(fields=["email"], name="users_email_idx"),
            models.Index(fields=["institution"], name="users_institution_idx"),
            models.Index(fields=["role"], name="users_role_idx"),
        ]

    def __str__(self):
        return self.email

    def save(self, *args, **kwargs):
        if self.email:
            self.email = UserManager.normalize_login_email(self.email)
        super().save(*args, **kwargs)

    def get_full_name(self):
        return self.name

    def get_short_name(self):
        return self.name.split(" ")[0] if self.name else self.email

    @property
    def is_student(self) -> bool:
        return self.role == UserRole.STUDENT

    @property
    def is_institution_staff(self) -> bool:
        return self.role == UserRole.INSTITUTION_STAFF

    @property
    def is_platform_admin(self) -> bool:
        """True for admin and super_admin — the platform-wide curator roles."""
        return self.role in ADMIN_ROLES

    @property
    def is_super_admin(self) -> bool:
        return self.role == UserRole.SUPER_ADMIN

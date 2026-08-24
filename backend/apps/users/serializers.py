"""User and authentication serializers.

Serializers own request shape and user-facing validation (§9.1).
"""

from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers

from apps.common import supabase_storage
from apps.common.exceptions import AuthenticationError
from apps.common.enums import ADMIN_ROLES, UserRole
from apps.users.managers import UserManager
from apps.users.models import User
from apps.users.services import register_user


class UserBriefSerializer(serializers.ModelSerializer):
    """Compact author/actor representation embedded in other payloads."""

    class Meta:
        model = User
        fields = ("id", "name", "email", "role", "avatar_url")
        read_only_fields = fields


class UserSerializer(serializers.ModelSerializer):
    """Full profile for ``/api/users/me/``."""

    institution = serializers.SerializerMethodField()
    institution_id = serializers.UUIDField(
        write_only=True, required=False, allow_null=True
    )
    avatar = serializers.ImageField(write_only=True, required=False)

    class Meta:
        model = User
        fields = (
            "id",
            "email",
            "name",
            "role",
            "avatar_url",
            "avatar",
            "institution",
            "institution_id",
            "is_active",
            "is_staff",
            "created_at",
            "updated_at",
        )
        read_only_fields = (
            "id",
            "email",
            "role",
            "avatar_url",
            "is_active",
            "is_staff",
            "created_at",
            "updated_at",
        )

    def get_institution(self, obj):
        if not obj.institution_id:
            return None
        institution = obj.institution
        return {
            "id": str(institution.id),
            "name": institution.name,
            "slug": institution.slug,
            "verified": institution.verified,
        }

    def validate_institution_id(self, value):
        if value is None:
            return None
        user = self.instance or self.context["request"].user
        # Staff ownership is derived from this field, so staff cannot move
        # themselves between institutions; an admin must do it for them.
        if user.role != UserRole.STUDENT:
            raise serializers.ValidationError(
                "Only an administrator can change the institution of a non-student account."
            )
        from apps.organizers.models import Institution

        if not Institution.objects.filter(pk=value).exists():
            raise serializers.ValidationError("Institution does not exist.")
        return value

    def update(self, instance, validated_data):
        avatar = validated_data.pop("avatar", None)
        institution_id = validated_data.pop("institution_id", serializers.empty)

        for field, value in validated_data.items():
            setattr(instance, field, value)

        if institution_id is not serializers.empty:
            instance.institution_id = institution_id

        if avatar is not None:
            supabase_storage.validate_image(avatar)
            path = supabase_storage.build_object_path("users", avatar, instance.id)
            instance.avatar_url = supabase_storage.replace(
                supabase_storage.AVATARS, instance.avatar_url, path, avatar
            )

        instance.save()
        return instance


class RegisterSerializer(serializers.Serializer):
    """
    Self-service registration.

    Only student accounts can be self-registered; elevated roles are granted by
    an administrator (§6).
    """

    email = serializers.EmailField()
    name = serializers.CharField(max_length=150)
    password = serializers.CharField(write_only=True, min_length=8, trim_whitespace=False)
    password_confirm = serializers.CharField(write_only=True, trim_whitespace=False)
    institution_id = serializers.UUIDField(required=False, allow_null=True)

    def validate_email(self, value):
        normalized = UserManager.normalize_login_email(value)
        if User.objects.filter(email=normalized).exists():
            raise serializers.ValidationError("An account with this email already exists.")
        return normalized

    def validate_institution_id(self, value):
        if value is None:
            return None
        from apps.organizers.models import Institution

        if not Institution.objects.filter(pk=value).exists():
            raise serializers.ValidationError("Institution does not exist.")
        return value

    def validate(self, attrs):
        if attrs["password"] != attrs.pop("password_confirm"):
            raise serializers.ValidationError({"password_confirm": "Passwords do not match."})
        return attrs

    def validate_password(self, value):
        try:
            validate_password(value)
        except DjangoValidationError as exc:
            raise serializers.ValidationError(list(exc.messages)) from exc
        return value

    def create(self, validated_data):
        return register_user(
            email=validated_data["email"],
            name=validated_data["name"],
            password=validated_data["password"],
            institution_id=validated_data.get("institution_id"),
        )


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, trim_whitespace=False)

    def validate(self, attrs):
        email = UserManager.normalize_login_email(attrs["email"])
        user = authenticate(
            request=self.context.get("request"), username=email, password=attrs["password"]
        )
        if user is None:
            # Django's ModelBackend refuses inactive users, so distinguish the
            # two cases explicitly for a useful message.
            if User.objects.filter(email=email, is_active=False).exists():
                raise AuthenticationError(
                    "This account has been suspended. Contact support.",
                    code="account_suspended",
                )
            raise AuthenticationError("Invalid email or password.", code="invalid_credentials")

        attrs["user"] = user
        return attrs


class UserAdminSerializer(serializers.ModelSerializer):
    """Administrative read view over accounts (§14)."""

    institution_name = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = (
            "id",
            "email",
            "name",
            "role",
            "institution",
            "institution_name",
            "is_active",
            "is_staff",
            "created_at",
        )
        read_only_fields = fields

    def get_institution_name(self, obj):
        return obj.institution.name if obj.institution_id else None


class RoleChangeSerializer(serializers.Serializer):
    """Payload for promoting or demoting an account."""

    role = serializers.ChoiceField(choices=UserRole.choices)

    def validate_role(self, value):
        actor = self.context["request"].user
        if value in ADMIN_ROLES and not actor.is_super_admin:
            raise serializers.ValidationError(
                "Only a super administrator may grant administrator roles."
            )
        if value == UserRole.SUPER_ADMIN and not actor.is_super_admin:
            raise serializers.ValidationError(
                "Only a super administrator may grant the super administrator role."
            )
        return value

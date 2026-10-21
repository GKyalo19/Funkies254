"""
Event serializers.

These own request shape, date ordering and the virtual/physical contradiction
checks (§4.4, §9.1). Hard invariants are additionally enforced by database
constraints.
"""

from rest_framework import serializers

from apps.common.enums import EventFormat, UserRole
from apps.events.models import Category, Event, SavedEvent, SchoolLevel, Section
from apps.organizers.models import Institution
from apps.organizers.serializers import InstitutionBriefSerializer
from apps.users.serializers import UserBriefSerializer


class SchoolLevelSerializer(serializers.ModelSerializer):
    class Meta:
        model = SchoolLevel
        fields = ("id", "name", "slug")
        read_only_fields = fields


class SectionBriefSerializer(serializers.ModelSerializer):
    class Meta:
        model = Section
        fields = ("id", "name", "slug", "description", "sort_order")
        read_only_fields = fields


class CategorySerializer(serializers.ModelSerializer):
    section = serializers.SlugRelatedField(slug_field="slug", read_only=True)

    class Meta:
        model = Category
        fields = ("id", "name", "slug", "section", "icon_url", "sort_order")
        read_only_fields = fields


class SectionSerializer(serializers.ModelSerializer):
    categories = serializers.SerializerMethodField()

    class Meta:
        model = Section
        fields = ("id", "name", "slug", "description", "sort_order", "categories")
        read_only_fields = fields

    def get_categories(self, obj):
        categories = getattr(obj, "active_categories", None)
        if categories is None:
            categories = obj.categories.filter(is_active=True).order_by("sort_order", "name")
        return CategorySerializer(categories, many=True).data


class EventSerializer(serializers.ModelSerializer):
    """Read representation of an event."""

    institution = InstitutionBriefSerializer(read_only=True)
    school_level = SchoolLevelSerializer(read_only=True)
    categories = CategorySerializer(many=True, read_only=True)
    created_by = UserBriefSerializer(read_only=True)
    verified_by = UserBriefSerializer(read_only=True)
    is_saved = serializers.SerializerMethodField()
    is_registered = serializers.SerializerMethodField()
    registration_count = serializers.SerializerMethodField()
    is_past = serializers.SerializerMethodField()
    is_virtual = serializers.SerializerMethodField()
    sections = serializers.SerializerMethodField()

    class Meta:
        model = Event
        fields = (
            "id",
            "title",
            "slug",
            "description",
            "institution",
            "start_time",
            "end_time",
            "venue",
            "location",
            "latitude",
            "longitude",
            "school_level",
            "categories",
            "cover_image_url",
            "registration_link",
            "format",
            "country",
            "is_free",
            "cost_note",
            "source",
            "popularity_score",
            "is_verified",
            "verified_by",
            "verified_at",
            "is_virtual",
            "is_past",
            "sections",
            "created_by",
            "is_saved",
            "is_registered",
            "registration_count",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields

    def _user(self):
        request = self.context.get("request")
        user = getattr(request, "user", None)
        return user if (user and user.is_authenticated) else None

    def get_is_virtual(self, obj):
        return obj.format == EventFormat.ONLINE

    def get_is_past(self, obj):
        return obj.is_past

    def get_sections(self, obj):
        seen = []
        slugs = set()
        for category in obj.categories.all():
            section = getattr(category, "section", None)
            if section is None or section.slug in slugs:
                continue
            slugs.add(section.slug)
            seen.append(SectionBriefSerializer(section).data)
        return seen

    def get_is_saved(self, obj):
        user = self._user()
        if user is None:
            return False
        saved_ids = self.context.get("saved_event_ids")
        if saved_ids is not None:
            return obj.id in saved_ids
        return SavedEvent.objects.filter(user=user, event=obj).exists()

    def get_is_registered(self, obj):
        user = self._user()
        if user is None:
            return False
        registered_ids = self.context.get("registered_event_ids")
        if registered_ids is not None:
            return obj.id in registered_ids
        from apps.registrations.models import EventRegistration

        return EventRegistration.objects.filter(
            user=user, event=obj, status=EventRegistration.ACTIVE_STATUS
        ).exists()

    def get_registration_count(self, obj):
        from apps.registrations.models import EventRegistration

        return EventRegistration.objects.filter(
            event=obj, status=EventRegistration.ACTIVE_STATUS
        ).count()


class EventWriteSerializer(serializers.ModelSerializer):
    """Create/update payload for institution staff and admins (§10.1)."""

    institution_id = serializers.PrimaryKeyRelatedField(
        source="institution",
        queryset=Institution.objects.all(),
        required=False,
        allow_null=True,
    )
    school_level_id = serializers.PrimaryKeyRelatedField(
        source="school_level",
        queryset=SchoolLevel.objects.all(),
        required=False,
        allow_null=True,
    )
    category_ids = serializers.PrimaryKeyRelatedField(
        source="categories",
        queryset=Category.objects.all(),
        many=True,
        required=False,
    )
    cover_image = serializers.ImageField(write_only=True, required=False)

    class Meta:
        model = Event
        fields = (
            "title",
            "description",
            "institution_id",
            "start_time",
            "end_time",
            "venue",
            "location",
            "latitude",
            "longitude",
            "school_level_id",
            "category_ids",
            "cover_image",
            "cover_image_url",
            "registration_link",
            "format",
            "country",
            "is_free",
            "cost_note",
            "is_virtual",
        )

    def validate_latitude(self, value):
        if value is not None and not -90 <= value <= 90:
            raise serializers.ValidationError("Latitude must be between -90 and 90.")
        return value

    def validate_longitude(self, value):
        if value is not None and not -180 <= value <= 180:
            raise serializers.ValidationError("Longitude must be between -180 and 180.")
        return value

    def validate(self, attrs):
        instance = self.instance
        start = attrs.get("start_time", getattr(instance, "start_time", None))
        end = attrs.get("end_time", getattr(instance, "end_time", None))

        if start and end and end <= start:
            raise serializers.ValidationError(
                {"end_time": "End time must be after the start time."}
            )

        if attrs.get("is_virtual") is True and "format" not in attrs:
            attrs["format"] = EventFormat.ONLINE
        elif attrs.get("is_virtual") is False and "format" not in attrs and instance is None:
            attrs["format"] = EventFormat.IN_PERSON

        event_format = attrs.get("format", getattr(instance, "format", EventFormat.IN_PERSON))
        link = attrs.get(
            "registration_link", getattr(instance, "registration_link", None) if instance else None
        )
        errors = {}
        if link and not str(link).startswith("https://"):
            errors["registration_link"] = "Registration link must start with https://."

        if event_format == EventFormat.ONLINE:
            for field in ("venue", "latitude", "longitude"):
                if attrs.get(field) is not None:
                    errors[field] = "An online event cannot have physical location data."
            if not link:
                errors["registration_link"] = (
                    "An online event needs a registration or joining link."
                )

        request = self.context.get("request")
        user = getattr(request, "user", None)
        publishing = (
            user is not None
            and getattr(user, "is_authenticated", False)
            and getattr(user, "is_platform_admin", False)
            and instance is None
        )
        if publishing and not (link and str(link).startswith("https://")):
            errors["registration_link"] = (
                "A published event needs an https:// registration link."
            )
        if errors:
            raise serializers.ValidationError(errors)

        self._validate_institution_ownership(attrs)
        return attrs

    def _validate_institution_ownership(self, attrs):
        """Staff may only attach events to their own institution (§10.1)."""
        request = self.context.get("request")
        user = getattr(request, "user", None)
        if user is None or not user.is_authenticated:
            return
        if user.role != UserRole.INSTITUTION_STAFF:
            return

        if not user.institution_id:
            raise serializers.ValidationError(
                {
                    "institution_id": "Your account is not linked to an institution. "
                    "Ask an administrator to link it before creating events."
                }
            )

        institution = attrs.get("institution", serializers.empty)
        if institution is serializers.empty:
            if self.instance is None:
                attrs["institution"] = user.institution
            return
        if institution is None or institution.id != user.institution_id:
            raise serializers.ValidationError(
                {"institution_id": "You may only create events for your own institution."}
            )


class SavedEventSerializer(serializers.ModelSerializer):
    event = EventSerializer(read_only=True)

    class Meta:
        model = SavedEvent
        fields = ("id", "event", "saved_at")
        read_only_fields = fields

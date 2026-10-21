"""Preference serializers."""

from decimal import Decimal, ROUND_HALF_UP

from django.db import transaction
from rest_framework import serializers

from apps.common.enums import EventFormat
from apps.events.models import Category, SchoolLevel, Section
from apps.events.serializers import CategorySerializer, SchoolLevelSerializer, SectionBriefSerializer
from apps.preferences.models import UserPreference, UserPreferenceCategory

DAY_CHOICES = {"weekdays", "weekends"}
DISTANCE_CHOICES = {10, 25, 50, 100}


class UserPreferenceSerializer(serializers.ModelSerializer):
    school_level = SchoolLevelSerializer(read_only=True)
    school_level_id = serializers.PrimaryKeyRelatedField(
        source="school_level",
        queryset=SchoolLevel.objects.all(),
        required=False,
        allow_null=True,
        write_only=True,
    )
    preferred_categories = CategorySerializer(many=True, read_only=True)
    preferred_category_ids = serializers.PrimaryKeyRelatedField(
        queryset=Category.objects.all(), many=True, required=False, write_only=True
    )
    sections = SectionBriefSerializer(many=True, read_only=True)
    section_ids = serializers.PrimaryKeyRelatedField(
        queryset=Section.objects.filter(is_active=True),
        many=True,
        required=False,
        write_only=True,
    )

    class Meta:
        model = UserPreference
        fields = (
            "id",
            "school_level",
            "school_level_id",
            "email_notifications",
            "push_notifications",
            "sections",
            "section_ids",
            "formats",
            "country",
            "city",
            "latitude",
            "longitude",
            "max_distance_km",
            "include_other_countries",
            "free_only",
            "days",
            "preferred_categories",
            "preferred_category_ids",
        )
        read_only_fields = ("id",)

    def validate_formats(self, value):
        allowed = {choice.value for choice in EventFormat}
        if not value or any(item not in allowed for item in value):
            raise serializers.ValidationError(
                "Choose one or more of in_person, online, hybrid."
            )
        return list(dict.fromkeys(value))

    def validate_days(self, value):
        if not value or any(item not in DAY_CHOICES for item in value):
            raise serializers.ValidationError("Choose weekdays, weekends, or both.")
        return list(dict.fromkeys(value))

    def validate_max_distance_km(self, value):
        if value is not None and value not in DISTANCE_CHOICES:
            raise serializers.ValidationError("Distance must be 10, 25, 50, 100, or empty.")
        return value

    def validate(self, attrs):
        latitude = attrs.get("latitude", serializers.empty)
        longitude = attrs.get("longitude", serializers.empty)
        if latitude is not serializers.empty:
            attrs["latitude"] = _round_coord(latitude)
        if longitude is not serializers.empty:
            attrs["longitude"] = _round_coord(longitude)
        return attrs

    @transaction.atomic
    def update(self, instance, validated_data):
        categories = validated_data.pop("preferred_category_ids", None)
        sections = validated_data.pop("section_ids", None)

        for field, value in validated_data.items():
            setattr(instance, field, value)
        instance.save()

        if categories is not None:
            UserPreferenceCategory.objects.filter(user_preference=instance).delete()
            UserPreferenceCategory.objects.bulk_create(
                [
                    UserPreferenceCategory(user_preference=instance, category=category)
                    for category in categories
                ],
                ignore_conflicts=True,
            )
        if sections is not None:
            instance.sections.set(sections)

        return instance


def _round_coord(value):
    if value is None:
        return None
    return Decimal(value).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

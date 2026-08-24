"""Preference serializers."""

from django.db import transaction
from rest_framework import serializers

from apps.events.models import Category, SchoolLevel
from apps.events.serializers import CategorySerializer, SchoolLevelSerializer
from apps.preferences.models import UserPreference, UserPreferenceCategory


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

    class Meta:
        model = UserPreference
        fields = (
            "id",
            "school_level",
            "school_level_id",
            "email_notifications",
            "push_notifications",
            "preferred_categories",
            "preferred_category_ids",
        )
        read_only_fields = ("id",)

    @transaction.atomic
    def update(self, instance, validated_data):
        categories = validated_data.pop("preferred_category_ids", None)

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

        return instance

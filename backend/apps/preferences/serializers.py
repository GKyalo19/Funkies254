from rest_framework import serializers

from apps.events.models import Category
from apps.events.serializers import CategorySerializer

from .models import UserPreference


class UserPreferenceSerializer(serializers.ModelSerializer):
    categories = serializers.PrimaryKeyRelatedField(many=True, queryset=Category.objects.all(), required=False)
    categories_detail = CategorySerializer(source="categories", many=True, read_only=True)

    class Meta:
        model = UserPreference
        fields = ["categories", "categories_detail", "education_levels", "preferred_locations", "max_days_ahead", "updated_at"]
        read_only_fields = ["updated_at"]

    def validate_education_levels(self, value):
        valid = {"high_school", "college", "both"}
        if not isinstance(value, list) or not all(v in valid for v in value):
            raise serializers.ValidationError(f"Each value must be one of {sorted(valid)}.")
        return value

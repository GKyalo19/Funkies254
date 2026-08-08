from rest_framework import serializers

from apps.organizers.serializers import OrganizerSerializer

from .models import Category, Event


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ["id", "name", "slug", "icon"]
        read_only_fields = ["id", "slug"]


class EventListSerializer(serializers.ModelSerializer):
    """Lightweight shape for event cards (home feed, listings, similar events)."""

    organizer_name = serializers.CharField(source="organizer.name", read_only=True)
    categories = CategorySerializer(many=True, read_only=True)
    is_free = serializers.BooleanField(read_only=True)
    is_registered = serializers.SerializerMethodField()

    class Meta:
        model = Event
        fields = [
            "id", "slug", "title", "short_description", "organizer_name",
            "categories", "education_level", "location", "start_datetime",
            "registration_fee", "is_free", "cover_image_url", "is_featured", "is_registered",
        ]

    def get_is_registered(self, obj):
        request = self.context.get("request")
        user = getattr(request, "user", None)
        if not user or not user.is_authenticated:
            return False
        return obj.registrations.filter(user=user, status="registered").exists()


class EventDetailSerializer(EventListSerializer):
    """Full shape for the single Event page — everything EventListSerializer has, plus more."""

    organizer = OrganizerSerializer(read_only=True)
    spots_left = serializers.IntegerField(read_only=True)
    registrations_count = serializers.IntegerField(read_only=True)

    class Meta(EventListSerializer.Meta):
        fields = EventListSerializer.Meta.fields + [
            "description", "venue_name", "address", "end_datetime", "capacity",
            "spots_left", "registrations_count", "external_registration_url",
            "organizer", "status", "created_at",
        ]


class EventWriteSerializer(serializers.ModelSerializer):
    """Used by staff to create/update events. Category IDs in, full objects out via the list/detail serializers."""

    categories = serializers.PrimaryKeyRelatedField(queryset=Category.objects.all(), many=True, required=False)

    class Meta:
        model = Event
        fields = [
            "title", "organizer", "categories", "short_description", "description",
            "education_level", "venue_name", "address", "location", "start_datetime",
            "end_datetime", "registration_fee", "capacity", "external_registration_url",
            "cover_image_url", "is_featured", "status",
        ]

    def create(self, validated_data):
        request = self.context.get("request")
        validated_data["created_by"] = getattr(request, "user", None)
        return super().create(validated_data)

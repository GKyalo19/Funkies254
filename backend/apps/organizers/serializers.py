from rest_framework import serializers

from .models import Organizer


class OrganizerSerializer(serializers.ModelSerializer):
    followers_count = serializers.IntegerField(read_only=True)
    is_following = serializers.SerializerMethodField()

    class Meta:
        model = Organizer
        fields = [
            "id", "name", "slug", "logo_url", "description", "website",
            "contact_email", "contact_phone", "years_hosting", "followers_count", "is_following",
        ]
        read_only_fields = ["id", "slug"]

    def get_is_following(self, obj):
        request = self.context.get("request")
        user = getattr(request, "user", None)
        if not user or not user.is_authenticated:
            return False
        return obj.followers.filter(user=user).exists()

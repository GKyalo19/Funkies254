from rest_framework import permissions
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.events.serializers import EventListSerializer

from .services import rank_events_for_user


class FeedView(APIView):
    """
    GET /api/recommendations/feed/?limit=20

    Backs the Home Page's "events in random-ish, personalised order" list.
    Works for anonymous visitors too (falls back to featured + soonest).
    """

    permission_classes = [permissions.AllowAny]

    def get(self, request):
        try:
            limit = min(int(request.query_params.get("limit", 20)), 50)
        except ValueError:
            limit = 20

        events = rank_events_for_user(request.user if request.user.is_authenticated else None, limit=limit)
        serializer = EventListSerializer(events, many=True, context={"request": request})
        return Response({"results": serializer.data, "count": len(serializer.data)})

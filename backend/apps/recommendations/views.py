"""Recommendation feed (§9, §12)."""

from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.events.models import SavedEvent
from apps.events.serializers import EventSerializer
from apps.recommendations.services import recommend_events


class RecommendationFeedView(APIView):
    """
    GET /api/recommendations/feed/

    Works for anonymous visitors (soonest upcoming events) and for signed-in
    students (preference-weighted, with the matching rules returned alongside
    each event so the UI can explain itself).
    """

    permission_classes = (AllowAny,)

    def get(self, request):
        limit = min(int(request.query_params.get("limit", 20) or 20), 50)
        user = request.user if request.user.is_authenticated else None
        scored = recommend_events(user=user, limit=limit)

        context = {"request": request}
        if user is not None:
            from apps.registrations.models import EventRegistration

            context["saved_event_ids"] = set(
                SavedEvent.objects.filter(user=user).values_list("event_id", flat=True)
            )
            context["registered_event_ids"] = set(
                EventRegistration.objects.filter(
                    user=user, status=EventRegistration.ACTIVE_STATUS
                ).values_list("event_id", flat=True)
            )

        return Response(
            {
                "count": len(scored),
                "personalised": user is not None,
                "results": [
                    {
                        "score": item.score,
                        "reasons": item.reasons,
                        "event": EventSerializer(item.event, context=context).data,
                    }
                    for item in scored
                ],
            }
        )

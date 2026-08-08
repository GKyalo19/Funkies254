"""
Rule-based event curation.

This is intentionally a plain scoring function, not a machine-learning
model — at this stage there isn't enough interaction data (views, past
registrations) to train anything meaningful, and a transparent, tunable
rule set is easier to debug and explain to users ("why am I seeing this?").

The public function `rank_events_for_user()` is the ONLY thing the view
layer calls. When there's enough behavioural data later, this function's
internals can be swapped for a real model (e.g. collaborative filtering
with `scikit-learn` or `implicit`) without touching any API contracts —
callers only ever see "a list of events, best match first".
"""
from datetime import timedelta

from django.utils import timezone

from apps.events.models import Event
from apps.organizers.models import Follow

# Tunable weights — kept as named constants so the scoring logic reads like
# a rubric and is easy to adjust after watching real usage.
WEIGHT_CATEGORY_MATCH = 10
WEIGHT_EDUCATION_LEVEL_MATCH = 6
WEIGHT_LOCATION_MATCH = 5
WEIGHT_FOLLOWED_ORGANIZER = 8
WEIGHT_FEATURED = 6
WEIGHT_SOON_MAX_BONUS = 5
CANDIDATE_POOL_SIZE = 300


def _base_queryset():
    now = timezone.now()
    return (
        Event.objects.filter(status="published", start_datetime__gte=now)
        .select_related("organizer")
        .prefetch_related("categories")
        .order_by("start_datetime")[:CANDIDATE_POOL_SIZE]
    )


def _soonness_bonus(event, now):
    """Events happening sooner get a small linear bonus, capped at WEIGHT_SOON_MAX_BONUS."""
    days_until = (event.start_datetime - now).days
    if days_until <= 0:
        return WEIGHT_SOON_MAX_BONUS
    return max(0, WEIGHT_SOON_MAX_BONUS - (days_until / 7))


def _score_event(event, preference, followed_organizer_ids, now):
    score = 0.0

    if preference is not None:
        event_category_ids = {c.id for c in event.categories.all()}
        preferred_category_ids = set(preference.categories.values_list("id", flat=True))
        matches = len(event_category_ids & preferred_category_ids)
        score += matches * WEIGHT_CATEGORY_MATCH

        if not preference.education_levels or event.education_level in preference.education_levels or event.education_level == "both":
            score += WEIGHT_EDUCATION_LEVEL_MATCH

        if not preference.preferred_locations or event.location in preference.preferred_locations:
            score += WEIGHT_LOCATION_MATCH

        days_until = (event.start_datetime - now).days
        if days_until > preference.max_days_ahead:
            score -= WEIGHT_CATEGORY_MATCH  # soft penalty, not a hard exclusion

    if event.organizer_id in followed_organizer_ids:
        score += WEIGHT_FOLLOWED_ORGANIZER

    if event.is_featured:
        score += WEIGHT_FEATURED

    score += _soonness_bonus(event, now)
    return score


def rank_events_for_user(user, limit=20):
    """
    Returns up to `limit` upcoming, published events ordered best-match-first
    for `user`. Anonymous users (or students with no preferences saved yet)
    get a sensible default: featured events first, then soonest.
    """
    now = timezone.now()
    candidates = list(_base_queryset())

    preference = None
    followed_organizer_ids = set()
    if user is not None and user.is_authenticated:
        preference = getattr(user, "preference", None)
        followed_organizer_ids = set(Follow.objects.filter(user=user).values_list("organizer_id", flat=True))

    scored = [(_score_event(event, preference, followed_organizer_ids, now), event) for event in candidates]
    scored.sort(key=lambda pair: (-pair[0], pair[1].start_datetime))

    return [event for _score, event in scored[:limit]]

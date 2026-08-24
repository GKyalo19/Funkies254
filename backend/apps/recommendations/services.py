"""
Rule-based recommendation engine (§12).

Deliberately transparent and free of machine learning: every point a candidate
event scores is explained by a named rule, and ties break on the soonest start
time then the event id, so the ranking is deterministic. Organizer follows and
featured events are intentionally absent because those tables are not part of
the confirmed schema (§12, §20).
"""

from dataclasses import dataclass, field

from django.utils import timezone

from apps.events.models import Event

CATEGORY_OVERLAP_POINTS = 3.0
CATEGORY_OVERLAP_MAX = 9.0
SCHOOL_LEVEL_POINTS = 2.5
LOCATION_POINTS = 2.0
INSTITUTION_POINTS = 1.5
HAPPENING_SOON_POINTS = 1.0
HAPPENING_SOON_DAYS = 14


@dataclass
class RecommendationProfile:
    """The signals a rule may consult, extracted once per request."""

    category_slugs: set = field(default_factory=set)
    school_level_id: str = None
    location_terms: set = field(default_factory=set)
    institution_id: str = None

    @property
    def is_empty(self) -> bool:
        return not (
            self.category_slugs
            or self.school_level_id
            or self.location_terms
            or self.institution_id
        )


@dataclass
class ScoredEvent:
    event: Event
    score: float
    reasons: list


def build_profile(user) -> RecommendationProfile:
    if user is None or not user.is_authenticated:
        return RecommendationProfile()

    profile = RecommendationProfile(institution_id=user.institution_id)

    preference = getattr(user, "preference", None)
    if preference is not None:
        profile.category_slugs = set(
            preference.preferred_categories.values_list("slug", flat=True)
        )
        profile.school_level_id = preference.school_level_id

    if user.institution_id and user.institution.location:
        profile.location_terms = _location_terms(user.institution.location)

    return profile


def score_event(event: Event, profile: RecommendationProfile) -> ScoredEvent:
    score = 0.0
    reasons = []

    if profile.category_slugs:
        overlap = profile.category_slugs.intersection(
            category.slug for category in event.categories.all()
        )
        if overlap:
            points = min(len(overlap) * CATEGORY_OVERLAP_POINTS, CATEGORY_OVERLAP_MAX)
            score += points
            reasons.append(
                {
                    "rule": "category_overlap",
                    "points": points,
                    "detail": f"Matches your interests: {', '.join(sorted(overlap))}.",
                }
            )

    if profile.school_level_id and event.school_level_id == profile.school_level_id:
        score += SCHOOL_LEVEL_POINTS
        reasons.append(
            {
                "rule": "school_level_match",
                "points": SCHOOL_LEVEL_POINTS,
                "detail": "Targets your school level.",
            }
        )

    if profile.location_terms and _location_terms(event.location or event.venue or "") & (
        profile.location_terms
    ):
        score += LOCATION_POINTS
        reasons.append(
            {
                "rule": "location_match",
                "points": LOCATION_POINTS,
                "detail": "Happening near you.",
            }
        )

    if profile.institution_id and event.institution_id == profile.institution_id:
        score += INSTITUTION_POINTS
        reasons.append(
            {
                "rule": "institution_match",
                "points": INSTITUTION_POINTS,
                "detail": "Hosted by your institution.",
            }
        )

    days_away = (event.start_time - timezone.now()).total_seconds() / 86400
    if 0 <= days_away <= HAPPENING_SOON_DAYS:
        points = round(
            HAPPENING_SOON_POINTS * (1 - days_away / HAPPENING_SOON_DAYS), 3
        )
        if points > 0:
            score += points
            reasons.append(
                {
                    "rule": "happening_soon",
                    "points": points,
                    "detail": "Starting soon.",
                }
            )

    return ScoredEvent(event=event, score=round(score, 3), reasons=reasons)


def recommend_events(*, user=None, limit=20, candidate_pool=200) -> list:
    """
    Return the highest scoring upcoming events for ``user``.

    Anonymous visitors get the deterministic fallback: the soonest upcoming
    verified events.
    """
    profile = build_profile(user)
    candidates = list(
        Event.objects.with_related()
        .visible_to(user)
        .verified()
        .upcoming()
        .order_by("start_time", "id")[:candidate_pool]
    )

    if profile.is_empty:
        return [ScoredEvent(event=event, score=0.0, reasons=[]) for event in candidates[:limit]]

    scored = [score_event(event, profile) for event in candidates]
    scored.sort(key=lambda item: (-item.score, item.event.start_time, str(item.event.id)))
    return scored[:limit]


def _location_terms(value: str) -> set:
    """Cheap, provider-neutral token match; geocoding stays out of the database (§4.4)."""
    tokens = {
        token.strip(",.;:()").lower()
        for token in (value or "").split()
        if len(token.strip(",.;:()")) > 2
    }
    return tokens

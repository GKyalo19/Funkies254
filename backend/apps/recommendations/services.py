"""
Rule-based recommendation engine (§12, RANK-1..RANK-3).

Weights live in RANKING_WEIGHTS so they can be tuned without touching the
rules. Every point is still explained by a named reason.
"""

import math
from dataclasses import dataclass, field
from datetime import datetime
from zoneinfo import ZoneInfo

from django.utils import timezone

from apps.common.enums import EventFormat
from apps.events.models import Event

NAIROBI = ZoneInfo("Africa/Nairobi")

RANKING_WEIGHTS = {
    "category_overlap": 3.0,
    "category_overlap_max": 9.0,
    "school_level": 2.5,
    "distance_max": 3.0,
    "distance_online": 1.5,
    "location_text": 2.0,
    "popularity_max": 3.0,
    "institution": 1.5,
    "happening_soon": 1.0,
    "happening_soon_days": 14,
    "distance_fallback_km": 300,
}


@dataclass
class RecommendationProfile:
    category_slugs: set = field(default_factory=set)
    school_level_id: str = None
    location_terms: set = field(default_factory=set)
    institution_id: str = None
    formats: set = field(default_factory=lambda: {choice.value for choice in EventFormat})
    free_only: bool = False
    days: set = field(default_factory=lambda: {"weekdays", "weekends"})
    country: str = "Kenya"
    include_other_countries: bool = False
    latitude: float = None
    longitude: float = None
    max_distance_km: int = None
    authenticated: bool = False

    @property
    def is_empty(self) -> bool:
        return not (
            self.category_slugs
            or self.school_level_id
            or self.location_terms
            or self.institution_id
            or self.latitude is not None
        )


@dataclass
class ScoredEvent:
    event: Event
    score: float
    reasons: list


def build_profile(user) -> RecommendationProfile:
    if user is None or not user.is_authenticated:
        return RecommendationProfile()

    profile = RecommendationProfile(
        institution_id=user.institution_id, authenticated=True
    )
    preference = getattr(user, "preference", None)
    if preference is not None:
        profile.category_slugs = set(
            preference.preferred_categories.values_list("slug", flat=True)
        )
        profile.school_level_id = preference.school_level_id
        profile.formats = set(preference.formats or profile.formats)
        profile.free_only = bool(preference.free_only)
        profile.days = set(preference.days or profile.days)
        profile.country = preference.country or "Kenya"
        profile.include_other_countries = bool(preference.include_other_countries)
        profile.max_distance_km = preference.max_distance_km
        if preference.latitude is not None and preference.longitude is not None:
            profile.latitude = float(preference.latitude)
            profile.longitude = float(preference.longitude)
        if preference.city:
            profile.location_terms |= _location_terms(preference.city)

    if user.institution_id and getattr(user.institution, "location", None):
        profile.location_terms |= _location_terms(user.institution.location)

    return profile


def _passes_hard_filters(event: Event, profile: RecommendationProfile) -> bool:
    if not profile.authenticated:
        return True
    if event.format not in profile.formats:
        return False
    if profile.free_only and not event.is_free:
        return False
    if not _day_matches(event, profile.days):
        return False
    if event.format == EventFormat.ONLINE:
        return True
    if not profile.include_other_countries:
        if (event.country or "Kenya").lower() != (profile.country or "Kenya").lower():
            return False
    if (
        profile.max_distance_km
        and profile.latitude is not None
        and event.latitude is not None
        and event.longitude is not None
    ):
        distance = haversine_km(
            profile.latitude, profile.longitude, float(event.latitude), float(event.longitude)
        )
        if distance > profile.max_distance_km:
            return False
    return True


def score_event(event: Event, profile: RecommendationProfile, *, max_popularity: float) -> ScoredEvent:
    weights = RANKING_WEIGHTS
    score = 0.0
    reasons = []

    if profile.category_slugs:
        overlap = profile.category_slugs.intersection(
            category.slug for category in event.categories.all()
        )
        if overlap:
            points = min(len(overlap) * weights["category_overlap"], weights["category_overlap_max"])
            score += points
            reasons.append(
                {
                    "rule": "category_overlap",
                    "points": points,
                    "detail": f"Matches your interests: {', '.join(sorted(overlap))}.",
                }
            )

    if profile.school_level_id and event.school_level_id == profile.school_level_id:
        score += weights["school_level"]
        reasons.append(
            {
                "rule": "school_level_match",
                "points": weights["school_level"],
                "detail": "Targets your school level.",
            }
        )

    distance_points, distance_reason = _distance_points(event, profile, max_km_weight=weights)
    if distance_points:
        score += distance_points
        reasons.append(distance_reason)

    if max_popularity > 0 and event.popularity_score:
        points = round(
            weights["popularity_max"] * (event.popularity_score / max_popularity), 3
        )
        if points > 0:
            score += points
            reasons.append(
                {
                    "rule": "popularity",
                    "points": points,
                    "detail": "Popular with students.",
                }
            )

    if profile.institution_id and event.institution_id == profile.institution_id:
        score += weights["institution"]
        reasons.append(
            {
                "rule": "institution_match",
                "points": weights["institution"],
                "detail": "Hosted by your institution.",
            }
        )

    days_away = (event.start_time - timezone.now()).total_seconds() / 86400
    window = weights["happening_soon_days"]
    if 0 <= days_away <= window:
        points = round(weights["happening_soon"] * (1 - days_away / window), 3)
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
    Upcoming verified events for ``user``.

    Visitors are ranked by popularity, then soonest start. Signed-in users are
    hard-filtered by their preferences and then scored.
    """
    profile = build_profile(user)
    candidates = [
        event
        for event in Event.objects.with_related()
        .visible_to(user)
        .verified()
        .upcoming()
        .order_by("-popularity_score", "start_time", "id")[:candidate_pool]
        if _passes_hard_filters(event, profile)
    ]

    if not profile.authenticated or profile.is_empty:
        ordered = sorted(candidates, key=lambda event: (-event.popularity_score, event.start_time, str(event.id)))
        return [ScoredEvent(event=event, score=0.0, reasons=[]) for event in ordered[:limit]]

    max_popularity = max((event.popularity_score or 0) for event in candidates) if candidates else 0
    scored = [score_event(event, profile, max_popularity=max_popularity) for event in candidates]
    scored.sort(key=lambda item: (-item.score, item.event.start_time, str(item.event.id)))
    return scored[:limit]


def haversine_km(lat1, lng1, lat2, lng2) -> float:
    radius = 6371.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    d_phi = math.radians(lat2 - lat1)
    d_lambda = math.radians(lng2 - lng1)
    a = math.sin(d_phi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(d_lambda / 2) ** 2
    return 2 * radius * math.asin(math.sqrt(a))


def _distance_points(event, profile, *, max_km_weight):
    if event.format == EventFormat.ONLINE:
        points = max_km_weight["distance_online"]
        return points, {
            "rule": "distance",
            "points": points,
            "detail": "Online, so you can join from anywhere.",
        }

    if (
        profile.latitude is not None
        and event.latitude is not None
        and event.longitude is not None
    ):
        km = haversine_km(
            profile.latitude, profile.longitude, float(event.latitude), float(event.longitude)
        )
        limit = profile.max_distance_km or max_km_weight["distance_fallback_km"]
        if km <= 10:
            points = max_km_weight["distance_max"]
        elif km >= limit:
            points = 0
        else:
            span = max(limit - 10, 1)
            points = round(max_km_weight["distance_max"] * (1 - (km - 10) / span), 3)
        if points <= 0:
            return 0, None
        return points, {
            "rule": "distance",
            "points": points,
            "detail": f"{round(km)} km from you.",
        }

    if profile.location_terms and _location_terms(event.location or event.venue or "") & profile.location_terms:
        points = max_km_weight["location_text"]
        return points, {
            "rule": "location_match",
            "points": points,
            "detail": "Happening near you.",
        }
    return 0, None


def _day_matches(event: Event, days: set) -> bool:
    if not days or days >= {"weekdays", "weekends"}:
        return True
    local = event.start_time.astimezone(NAIROBI)
    if not isinstance(local, datetime):
        return True
    is_weekend = local.weekday() >= 5
    if is_weekend:
        return "weekends" in days
    return "weekdays" in days


def _location_terms(value: str) -> set:
    return {
        token.strip(",.;:()").lower()
        for token in (value or "").split()
        if len(token.strip(",.;:()")) > 2
    }

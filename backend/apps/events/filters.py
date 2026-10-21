"""Event filtering for the public listing endpoint."""

import math

import django_filters as filters
from django.utils import timezone

from apps.events.models import Event


class EventFilter(filters.FilterSet):
    """
    Supported query parameters::

        ?category=sports&category=math
        ?section=college-events          repeatable
        ?school_level=college
        ?format=online
        ?country=Kenya
        ?is_free=true
        ?near=-1.29,36.82&radius_km=25
        ?upcoming=true                   default true unless ?search= is set
        ?search=chess
    """

    category = filters.CharFilter(method="filter_category")
    section = filters.CharFilter(method="filter_section")
    school_level = filters.CharFilter(field_name="school_level__slug", lookup_expr="iexact")
    institution_slug = filters.CharFilter(field_name="institution__slug", lookup_expr="iexact")
    start_after = filters.IsoDateTimeFilter(field_name="start_time", lookup_expr="gte")
    start_before = filters.IsoDateTimeFilter(field_name="start_time", lookup_expr="lte")
    upcoming = filters.BooleanFilter(method="filter_upcoming")
    is_free = filters.BooleanFilter(field_name="is_free")
    country = filters.CharFilter(field_name="country", lookup_expr="iexact")
    near = filters.CharFilter(method="filter_near")

    class Meta:
        model = Event
        fields = (
            "category",
            "section",
            "school_level",
            "institution",
            "institution_slug",
            "format",
            "is_virtual",
            "is_verified",
            "is_free",
            "country",
            "start_after",
            "start_before",
            "upcoming",
        )

    def filter_category(self, queryset, name, value):
        slugs = [slug for slug in self.request.GET.getlist("category") if slug] or [value]
        return queryset.filter(categories__slug__in=slugs).distinct()

    def filter_section(self, queryset, name, value):
        slugs = [slug for slug in self.request.GET.getlist("section") if slug] or [value]
        return queryset.filter(categories__section__slug__in=slugs).distinct()

    def filter_upcoming(self, queryset, name, value):
        if value is None:
            return queryset
        now = timezone.now()
        return queryset.filter(end_time__gte=now) if value else queryset.filter(end_time__lt=now)

    def filter_near(self, queryset, name, value):
        radius = self.request.GET.get("radius_km") or "25"
        try:
            lat_raw, lng_raw = value.split(",", 1)
            lat = float(lat_raw)
            lng = float(lng_raw)
            radius_km = float(radius)
        except (TypeError, ValueError):
            return queryset.none()
        if radius_km <= 0:
            return queryset.none()
        delta_lat = radius_km / 111.0
        cos_lat = math.cos(math.radians(lat)) or 0.01
        delta_lng = radius_km / (111.0 * abs(cos_lat))
        return queryset.filter(
            latitude__gte=lat - delta_lat,
            latitude__lte=lat + delta_lat,
            longitude__gte=lng - delta_lng,
            longitude__lte=lng + delta_lng,
        ).exclude(format="online")

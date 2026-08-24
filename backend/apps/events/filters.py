"""Event filtering for the public listing endpoint."""

import django_filters as filters
from django.utils import timezone

from apps.events.models import Event


class EventFilter(filters.FilterSet):
    """
    Supported query parameters::

        ?category=sports&category=math      one or more category slugs
        ?school_level=college               school level slug
        ?institution=<uuid>                 institution id
        ?institution_slug=nairobi-school    institution slug
        ?is_virtual=true
        ?is_verified=true
        ?start_after=2026-09-01T00:00:00Z
        ?start_before=2026-09-30T00:00:00Z
        ?upcoming=true                      hides events that already ended
        ?search=chess                       title/description/venue/location
    """

    category = filters.CharFilter(method="filter_category")
    school_level = filters.CharFilter(field_name="school_level__slug", lookup_expr="iexact")
    institution_slug = filters.CharFilter(field_name="institution__slug", lookup_expr="iexact")
    start_after = filters.IsoDateTimeFilter(field_name="start_time", lookup_expr="gte")
    start_before = filters.IsoDateTimeFilter(field_name="start_time", lookup_expr="lte")
    upcoming = filters.BooleanFilter(method="filter_upcoming")

    class Meta:
        model = Event
        fields = (
            "category",
            "school_level",
            "institution",
            "institution_slug",
            "is_virtual",
            "is_verified",
            "start_after",
            "start_before",
            "upcoming",
        )

    def filter_category(self, queryset, name, value):
        slugs = [slug for slug in self.request.GET.getlist("category") if slug] or [value]
        return queryset.filter(categories__slug__in=slugs).distinct()

    def filter_upcoming(self, queryset, name, value):
        if value is None:
            return queryset
        now = timezone.now()
        return queryset.filter(end_time__gte=now) if value else queryset.filter(end_time__lt=now)

import django_filters as filters

from .models import Event


class EventFilter(filters.FilterSet):
    """
    Powers the Event Listings page filter panel from the Figma design:
    category, location, date range, registration fee (free/paid), and
    education level all map 1:1 to a query param here.
    """

    category = filters.CharFilter(field_name="categories__slug", lookup_expr="iexact")
    location = filters.CharFilter(field_name="location", lookup_expr="icontains")
    education_level = filters.CharFilter(field_name="education_level", lookup_expr="iexact")
    date_from = filters.IsoDateTimeFilter(field_name="start_datetime", lookup_expr="gte")
    date_to = filters.IsoDateTimeFilter(field_name="start_datetime", lookup_expr="lte")
    fee = filters.ChoiceFilter(method="filter_fee", choices=[("free", "Free"), ("paid", "Paid")])
    is_featured = filters.BooleanFilter(field_name="is_featured")

    class Meta:
        model = Event
        fields = ["category", "location", "education_level", "date_from", "date_to", "fee", "is_featured"]

    def filter_fee(self, queryset, name, value):
        if value == "free":
            return queryset.filter(registration_fee=0)
        if value == "paid":
            return queryset.filter(registration_fee__gt=0)
        return queryset

"""Filters for the administrative user listing."""

import django_filters as filters

from apps.users.models import User


class UserFilter(filters.FilterSet):
    affiliation = filters.CharFilter(
        field_name="institution_affiliation", lookup_expr="icontains"
    )
    created_after = filters.IsoDateTimeFilter(field_name="created_at", lookup_expr="gte")
    created_before = filters.IsoDateTimeFilter(field_name="created_at", lookup_expr="lte")

    class Meta:
        model = User
        fields = ("role", "is_active", "institution")

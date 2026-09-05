"""Problem filters (spec 13)."""

from __future__ import annotations

from django_filters import rest_framework as filters

from jandrishti.modules.catalog.models import Category, Department

from ..domain.enums import ProblemPriority, ProblemStatus
from ..models import Problem


class ProblemFilter(filters.FilterSet):
    category = filters.CharFilter(method="filter_category")
    department = filters.CharFilter(method="filter_department")
    state = filters.CharFilter(field_name="state", lookup_expr="iexact")
    district = filters.CharFilter(field_name="district", lookup_expr="iexact")
    city = filters.CharFilter(field_name="city", lookup_expr="iexact")
    pincode = filters.CharFilter(field_name="pincode")
    status = filters.MultipleChoiceFilter(choices=ProblemStatus.choices)
    priority = filters.MultipleChoiceFilter(choices=ProblemPriority.choices)
    is_open = filters.BooleanFilter(method="filter_is_open")
    has_evidence = filters.BooleanFilter(method="filter_has_evidence")
    verified_evidence = filters.BooleanFilter(method="filter_verified_evidence")
    cluster = filters.CharFilter(field_name="cluster__public_id")
    min_support = filters.NumberFilter(field_name="support_count", lookup_expr="gte")
    since = filters.IsoDateTimeFilter(field_name="created_at", lookup_expr="gte")
    until = filters.IsoDateTimeFilter(field_name="created_at", lookup_expr="lte")
    q = filters.CharFilter(method="filter_search")

    class Meta:
        model = Problem
        fields = ["state", "district", "city", "status", "priority"]

    def filter_category(self, queryset, name, value):
        """Filtering by a parent category includes its whole subtree.

        Asking for `Infrastructure` and getting nothing because every problem is
        filed under `Infrastructure > Roads` would be a bug, not a feature.
        """
        category = (
            Category.objects.filter(public_id=value).first()
            or Category.objects.filter(slug=value).first()
        )
        if category is None:
            return queryset.none()
        return queryset.filter(category__path__in=[category.path]) | queryset.filter(
            category__path__startswith=f"{category.path}/"
        )

    def filter_department(self, queryset, name, value):
        department = Department.objects.filter(public_id=value).first()
        if department is None:
            return queryset.none()
        return queryset.filter(department__path__startswith=department.path)

    def filter_is_open(self, queryset, name, value):
        statuses = ProblemStatus.open_statuses() if value else ProblemStatus.closed_statuses()
        return queryset.filter(status__in=statuses)

    def filter_has_evidence(self, queryset, name, value):
        return queryset.filter(evidence_count__gt=0) if value else queryset.filter(evidence_count=0)

    def filter_verified_evidence(self, queryset, name, value):
        """Problems carrying at least one file a human has verified."""
        if not value:
            return queryset
        from jandrishti.modules.media.models import MediaAttachment, VerificationStatus

        verified_ids = MediaAttachment.objects.filter(
            target_type=MediaAttachment.Target.PROBLEM,
            media__verification_status=VerificationStatus.VERIFIED,
        ).values_list("target_id", flat=True)
        return queryset.filter(id__in=verified_ids)

    def filter_search(self, queryset, name, value):
        """Free text within the current filter set.

        Delegated to the search module so that swapping PostgreSQL full text for
        OpenSearch later changes one adapter, not this filter (spec 52).
        """
        from jandrishti.modules.search.application.service import search_service

        return search_service.filter_problems(queryset, value)

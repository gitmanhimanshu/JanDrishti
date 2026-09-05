"""
Ranking strategies (spec 39).

Each tab on the Problems page is a strategy object. Adding "Most discussed"
means writing one class and registering it -- no existing strategy is touched,
which is the Open/Closed Principle doing actual work rather than decorating a
diagram.

A strategy returns an ordered queryset. It never fetches, so the caller can
still filter and paginate on top of it.
"""

from __future__ import annotations

import math
from abc import ABC, abstractmethod
from datetime import timedelta
from typing import Any, ClassVar

from django.conf import settings
from django.db.models import Case, F, FloatField, QuerySet, Value, When
from django.utils import timezone

from jandrishti.shared.domain.value_objects import GeoPoint

from .enums import ProblemPriority, ProblemStatus


class RankingStrategy(ABC):
    """Orders a problem queryset. One tab, one strategy."""

    key: ClassVar[str] = ""
    label: ClassVar[str] = ""
    description: ClassVar[str] = ""

    @abstractmethod
    def apply(self, queryset: QuerySet, **context: Any) -> QuerySet: ...

    def describe(self) -> dict[str, str]:
        return {"key": self.key, "label": self.label, "description": self.description}


def compute_trend_score(
    *,
    support_count: int,
    report_count: int,
    comment_count: int,
    last_activity_at,
    now=None,
) -> float:
    """Momentum, not raw totals.

    Engagement is log-damped so one viral issue cannot permanently own the tab,
    then divided by age: an issue picking up 40 supporters this week outranks
    one that collected 300 two years ago, which is what a citizen means by
    `trending`. Independent reports weigh double a support, because filing your
    own report is a stronger signal than tapping a button on someone else's.

    A pure function on purpose. It is called when engagement changes and the
    result is stored -- recomputing a decay curve for every row on every page
    load is exactly the thing section 67 forbids.
    """
    now = now or timezone.now()
    half_life_hours = float(getattr(settings, "TRENDING_HALF_LIFE_HOURS", 36))
    engagement = math.log1p(
        max(support_count, 0) + max(report_count, 0) * 2 + max(comment_count, 0)
    )
    age_hours = max((now - last_activity_at).total_seconds() / 3600.0, 0.0)
    return round(engagement / (1.0 + age_hours / half_life_hours), 6)


class TrendingRankingStrategy(RankingStrategy):
    """Orders by the stored trend score.

    The score is refreshed when engagement changes and re-decayed periodically
    by a Celery task, so this tab is a plain indexed sort.
    """

    key = "trending"
    label = "Trending"
    description = "Recent engagement and momentum."

    def apply(self, queryset: QuerySet, **context: Any) -> QuerySet:
        return queryset.order_by("-trend_score", "-last_activity_at")


class MostSupportedRankingStrategy(RankingStrategy):
    key = "most_supported"
    label = "Most Supported"
    description = "Highest number of unique supporters."

    def apply(self, queryset: QuerySet, **context: Any) -> QuerySet:
        return queryset.order_by("-support_count", "-created_at")


class MostReportedRankingStrategy(RankingStrategy):
    """Independent reports, not supports.

    Distinct from Most Supported on purpose: 500 people each filing their own
    report about the same pothole is a different and stronger signal than 500
    people tapping support on one report (spec 19).
    """

    key = "most_reported"
    label = "Most Reported"
    description = "Highest number of independent reports."

    def apply(self, queryset: QuerySet, **context: Any) -> QuerySet:
        return queryset.order_by("-report_count", "-support_count", "-created_at")


class HighPriorityRankingStrategy(RankingStrategy):
    key = "high_priority"
    label = "High Priority"
    description = "Urgent and important issues first."

    def apply(self, queryset: QuerySet, **context: Any) -> QuerySet:
        priority_rank = Case(
            *[
                When(priority=value, then=Value(ProblemPriority.weight(value)))
                for value in ProblemPriority.values
            ],
            default=Value(0),
            output_field=FloatField(),
        )
        return queryset.annotate(priority_rank=priority_rank).order_by(
            "-priority_rank", "-support_count", "-created_at"
        )


class NearbyRankingStrategy(RankingStrategy):
    """Distance-ordered, and only when the user has offered a location.

    A bounding box prefilters on the (latitude, longitude) index before the
    trigonometry runs, so this stays cheap on a table with millions of rows.
    """

    key = "nearby"
    label = "Nearby"
    description = "Issues closest to you."

    def apply(self, queryset: QuerySet, **context: Any) -> QuerySet:
        latitude = context.get("latitude")
        longitude = context.get("longitude")
        if latitude is None or longitude is None:
            # No location offered: fall back rather than returning nothing.
            return queryset.order_by("-last_activity_at")

        radius_km = float(context.get("radius_km") or settings.NEARBY_DEFAULT_RADIUS_KM)
        origin = GeoPoint(float(latitude), float(longitude))
        min_lat, max_lat, min_lng, max_lng = origin.bounding_box(radius_km)

        # Squared planar distance is monotonic with real distance over a few
        # kilometres, and it orders correctly without a trig function per row.
        # Longitude is scaled by cos(latitude) so the ordering stays honest.
        import math

        lng_scale = math.cos(math.radians(origin.latitude)) ** 2
        return (
            queryset.filter(
                latitude__gte=min_lat,
                latitude__lte=max_lat,
                longitude__gte=min_lng,
                longitude__lte=max_lng,
            )
            .annotate(
                distance_sq=(F("latitude") - Value(origin.latitude))
                * (F("latitude") - Value(origin.latitude))
                + (F("longitude") - Value(origin.longitude))
                * (F("longitude") - Value(origin.longitude))
                * Value(lng_scale)
            )
            .order_by("distance_sq", "-support_count")
        )


class RecentlyReportedRankingStrategy(RankingStrategy):
    key = "recent"
    label = "Recently Reported"
    description = "The latest issues raised."

    def apply(self, queryset: QuerySet, **context: Any) -> QuerySet:
        return queryset.order_by("-created_at")


class RecentlyUpdatedRankingStrategy(RankingStrategy):
    key = "recently_updated"
    label = "Recently Updated"
    description = "Latest government and project updates."

    def apply(self, queryset: QuerySet, **context: Any) -> QuerySet:
        return queryset.exclude(last_status_change_at__isnull=True).order_by(
            "-last_status_change_at"
        )


class ResolvedRankingStrategy(RankingStrategy):
    key = "resolved"
    label = "Resolved"
    description = "Issues that were actually fixed."

    def apply(self, queryset: QuerySet, **context: Any) -> QuerySet:
        return queryset.filter(status=ProblemStatus.RESOLVED).order_by("-resolved_at")


class StaleRankingStrategy(RankingStrategy):
    """Open, well-supported and untouched for a fortnight.

    Not in the spec, but it is what accountability looks like in practice: the
    issues nobody has moved are the ones worth surfacing.
    """

    key = "stale"
    label = "Awaiting Action"
    description = "Supported issues with no update in a while."

    def apply(self, queryset: QuerySet, **context: Any) -> QuerySet:
        cutoff = timezone.now() - timedelta(days=14)
        return (
            queryset.filter(
                status__in=ProblemStatus.open_statuses(), last_status_change_at__lt=cutoff
            )
            .filter(support_count__gte=5)
            .order_by("last_status_change_at", "-support_count")
        )


class RankingRegistry:
    """Strategy lookup. Registration is the only thing a new tab has to do."""

    def __init__(self) -> None:
        self._strategies: dict[str, RankingStrategy] = {}

    def register(self, strategy: RankingStrategy) -> RankingStrategy:
        self._strategies[strategy.key] = strategy
        return strategy

    def get(self, key: str | None) -> RankingStrategy:
        return self._strategies.get(key or "", self._strategies["trending"])

    def all(self) -> list[RankingStrategy]:
        return list(self._strategies.values())


ranking_registry = RankingRegistry()
for _strategy in (
    TrendingRankingStrategy(),
    MostSupportedRankingStrategy(),
    MostReportedRankingStrategy(),
    HighPriorityRankingStrategy(),
    NearbyRankingStrategy(),
    RecentlyReportedRankingStrategy(),
    RecentlyUpdatedRankingStrategy(),
    ResolvedRankingStrategy(),
    StaleRankingStrategy(),
):
    ranking_registry.register(_strategy)

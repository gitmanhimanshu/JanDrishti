"""
Department routing service.

Spec 37 is explicit that routing logic must not live inside API views. This is
the one place that answers "who is responsible for this problem", and both the
citizen submission path and the government dashboard call it.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

from django.db.models import Q

from ..models import Category, Department, RoutingRule

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class RoutingDecision:
    department: Department | None
    rule: RoutingRule | None
    confidence: str  # exact | category | inherited | none
    reason: str


class DepartmentRoutingService:
    """Resolves category plus location to a department.

    Resolution order, most specific first:
      1. a rule for this exact category and the tightest matching jurisdiction,
      2. the same for an ancestor category (a rule on Infrastructure covers
         Roads unless Roads has its own),
      3. nothing -- the problem stays unassigned for a human to route, which is
         the honest answer and better than a wrong department.
    """

    def route(
        self,
        *,
        category: Category | None,
        state: str = "",
        district: str = "",
        city: str = "",
    ) -> RoutingDecision:
        if category is None:
            return RoutingDecision(None, None, "none", "No category was supplied.")

        category_ids = self._category_lineage_ids(category)

        # Jurisdiction fields match when the rule leaves them blank (wildcard)
        # or when they equal the problem location, case-insensitively.
        jurisdiction = Q()
        for field, value in (("state", state), ("district", district), ("city", city)):
            jurisdiction &= Q(**{f"{field}": ""}) | Q(**{f"{field}__iexact": value or ""})

        rules = list(
            RoutingRule.objects.select_related("department", "category")
            .filter(is_active=True, category_id__in=category_ids)
            .filter(jurisdiction)
            .order_by("-specificity")
        )
        if not rules:
            return RoutingDecision(
                None, None, "none", "No routing rule matches this category and location yet."
            )

        # Prefer a rule on the exact category over one inherited from an
        # ancestor, then prefer the most specific jurisdiction.
        rules.sort(key=lambda r: (r.category_id == category.id, r.specificity), reverse=True)
        best = rules[0]
        confidence = "exact" if best.category_id == category.id else "inherited"
        return RoutingDecision(
            department=best.department,
            rule=best,
            confidence=confidence,
            reason=f"Matched rule {best.pk} ({confidence}).",
        )

    @staticmethod
    def _category_lineage_ids(category: Category) -> list[int]:
        """The category itself plus its ancestors, nearest first."""
        slugs = category.path.split("/")
        paths = ["/".join(slugs[: i + 1]) for i in range(len(slugs))]
        lineage = Category.objects.filter(path__in=paths).order_by("-depth")
        return [c.id for c in lineage]


routing_service = DepartmentRoutingService()


def suggest_department(**kwargs) -> Department | None:
    return routing_service.route(**kwargs).department

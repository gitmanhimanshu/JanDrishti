"""
Public impact statistics (spec 12).

Two rules this file exists to keep:

1. No fabricated numbers. Everything here is an aggregate over real rows; an
   empty platform reports zeros, and the frontend shows honest empty states.
2. No aggregate recomputed per request. The landing page is the most-hit
   endpoint on the site, so the counts are cached and refreshed on a schedule.
"""

from __future__ import annotations

from django.db.models import Avg, Count, Q
from django.utils import timezone
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from jandrishti.shared.api.response import ok
from jandrishti.shared.infrastructure.cache import cache_gateway

STATS_CACHE_KEY = "public_stats:v1"
STATS_TTL_SECONDS = 300


def compute_public_stats() -> dict:
    from jandrishti.modules.experience.models import Experience
    from jandrishti.modules.problems.domain.enums import ProblemStatus
    from jandrishti.modules.problems.models import GovernmentResponse, Problem
    from jandrishti.modules.projects.models import Project, ProjectStatus

    problems = Problem.objects.public()
    problem_stats = problems.aggregate(
        total=Count("id"),
        active=Count("id", filter=Q(status__in=ProblemStatus.open_statuses())),
        resolved=Count("id", filter=Q(status=ProblemStatus.RESOLVED)),
        supporters=Count("supports", distinct=True),
    )

    # Average days from report to resolution -- the number that actually tells a
    # citizen whether reporting is worth their time.
    resolved = problems.filter(status=ProblemStatus.RESOLVED, resolved_at__isnull=False)
    durations = [
        (problem.resolved_at - problem.created_at).days
        for problem in resolved.only("created_at", "resolved_at")[:1000]
    ]
    avg_resolution_days = round(sum(durations) / len(durations), 1) if durations else None

    return {
        "problems_reported": problem_stats["total"],
        "active_problems": problem_stats["active"],
        "problems_resolved": problem_stats["resolved"],
        "citizens_supporting": problem_stats["supporters"],
        "experiences_shared": Experience.objects.public().count(),
        "government_responses": GovernmentResponse.objects.count(),
        "projects_completed": Project.objects.filter(
            status__in=[ProjectStatus.COMPLETED, ProjectStatus.VERIFIED]
        ).count(),
        "average_resolution_days": avg_resolution_days,
        "computed_at": timezone.now().isoformat(),
    }


class PublicStatsView(APIView):
    """The landing page counters."""

    def get(self, request: Request) -> Response:
        stats = cache_gateway.get_or_set(STATS_CACHE_KEY, compute_public_stats, STATS_TTL_SECONDS)
        return ok(stats)


class DepartmentPerformanceView(APIView):
    """Accountability by department: volume, resolution rate, average time."""

    def get(self, request: Request) -> Response:
        from jandrishti.modules.problems.domain.enums import ProblemStatus
        from jandrishti.modules.problems.models import Problem

        rows = (
            Problem.objects.public()
            .exclude(department__isnull=True)
            .values("department__public_id", "department__name", "department__state")
            .annotate(
                total=Count("id"),
                resolved=Count("id", filter=Q(status=ProblemStatus.RESOLVED)),
                open=Count("id", filter=Q(status__in=ProblemStatus.open_statuses())),
                avg_support=Avg("support_count"),
            )
            .order_by("-total")[:100]
        )
        return ok(
            [
                {
                    "department_id": str(row["department__public_id"]),
                    "department": row["department__name"],
                    "state": row["department__state"],
                    "total": row["total"],
                    "resolved": row["resolved"],
                    "open": row["open"],
                    "resolution_rate": (
                        round(row["resolved"] / row["total"] * 100, 1) if row["total"] else 0.0
                    ),
                    "average_support": round(row["avg_support"] or 0, 1),
                }
                for row in rows
            ]
        )

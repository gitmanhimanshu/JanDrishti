"""Unified search across problems, experiences and projects."""

from __future__ import annotations

from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from jandrishti.shared.api.response import ok

from ..application.service import search_service

PER_TYPE_LIMIT = 10


class UnifiedSearchView(APIView):
    """GET /api/v1/search/?q=... -- public, capped, no pagination games.

    Returns a small slice of each content type. Deep results come from the
    per-section list endpoints, which paginate properly.
    """

    def get(self, request: Request) -> Response:
        query = (request.query_params.get("q") or "").strip()
        if len(query) < 2:
            return ok({"query": query, "problems": [], "experiences": [], "projects": []})

        from jandrishti.modules.experience.api.serializers import ExperienceCardSerializer
        from jandrishti.modules.experience.models import Experience
        from jandrishti.modules.problems.api.serializers import ProblemCardSerializer
        from jandrishti.modules.problems.models import Problem
        from jandrishti.modules.projects.api.views import ProjectSerializer
        from jandrishti.modules.projects.models import Project

        problems = list(
            search_service.filter_problems(
                Problem.objects.public().with_display_relations(), query
            )[:PER_TYPE_LIMIT]
        )
        experiences = list(
            search_service.filter_experiences(
                Experience.objects.public().with_display_relations(), query
            )[:PER_TYPE_LIMIT]
        )
        projects = list(
            Project.objects.select_related("department").filter(title__icontains=query)[
                :PER_TYPE_LIMIT
            ]
        )

        context = {"request": request}
        return ok(
            {
                "query": query,
                "problems": ProblemCardSerializer(problems, many=True, context=context).data,
                "experiences": ExperienceCardSerializer(
                    experiences, many=True, context=context
                ).data,
                "projects": ProjectSerializer(projects, many=True, context=context).data,
            }
        )

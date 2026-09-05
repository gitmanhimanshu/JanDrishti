"""Public catalog endpoints: categories, departments, states."""

from __future__ import annotations

from django.db.models import Count, Q
from rest_framework import serializers
from rest_framework.generics import ListAPIView
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from jandrishti.shared.api.response import ok

from ..models import Category, Department


class CategorySerializer(serializers.ModelSerializer):
    id = serializers.UUIDField(source="public_id", read_only=True)
    children = serializers.SerializerMethodField()

    class Meta:
        model = Category
        fields = ["id", "name", "slug", "path", "depth", "icon", "description", "children"]

    def get_children(self, obj: Category) -> list[dict]:
        # `prefetched_children` is set by the list view so this stays one query.
        children = getattr(obj, "prefetched_children", None)
        if children is None:
            return []
        return CategorySerializer(children, many=True).data


class DepartmentSerializer(serializers.ModelSerializer):
    id = serializers.UUIDField(source="public_id", read_only=True)

    class Meta:
        model = Department
        fields = [
            "id",
            "name",
            "slug",
            "path",
            "level",
            "state",
            "district",
            "city",
            "avg_resolution_days",
            "resolved_count",
        ]


class CategoryTreeView(APIView):
    """The whole active category tree in one response.

    Small, near-static and read on every page -- exactly the shape that should
    be assembled once and cached rather than fetched per request.
    """

    def get(self, request: Request) -> Response:
        categories = list(Category.objects.active().order_by("depth", "display_order", "name"))
        by_parent: dict[int | None, list[Category]] = {}
        for category in categories:
            by_parent.setdefault(category.parent_id, []).append(category)
        for category in categories:
            category.prefetched_children = by_parent.get(category.id, [])  # type: ignore[attr-defined]
        roots = by_parent.get(None, [])
        return ok(CategorySerializer(roots, many=True).data)


class DepartmentListView(ListAPIView):
    serializer_class = DepartmentSerializer
    queryset = Department.objects.active().order_by("state", "display_order", "name")
    filterset_fields = ["state", "district", "city", "level"]


class StateListView(APIView):
    """States that actually have reported problems, with counts.

    Derived from data rather than a hardcoded list, so the discovery page never
    advertises a state with nothing in it (spec 12: no fake statistics).
    """

    def get(self, request: Request) -> Response:
        from jandrishti.modules.problems.models import Problem

        rows = (
            Problem.objects.public()
            .exclude(state="")
            .values("state")
            .annotate(
                problem_count=Count("id"),
                resolved_count=Count("id", filter=Q(status="RESOLVED")),
            )
            .order_by("-problem_count")
        )
        return ok(list(rows))

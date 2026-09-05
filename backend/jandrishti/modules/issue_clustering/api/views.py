"""Cluster endpoints: public read, moderator merge and detach."""

from __future__ import annotations

from rest_framework import serializers
from rest_framework.generics import ListAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from jandrishti.shared.api.pagination import StandardPageNumberPagination
from jandrishti.shared.api.permissions import IsModerator
from jandrishti.shared.api.response import error, ok
from jandrishti.shared.api.views import ActorMixin

from ..application.service import clustering_service
from ..models import ClusterStatus, IssueCluster


class ClusterSerializer(serializers.ModelSerializer):
    id = serializers.UUIDField(source="public_id", read_only=True)
    aggregate_label = serializers.CharField(read_only=True)
    category_name = serializers.CharField(source="category.name", default="", read_only=True)
    department_name = serializers.CharField(source="department.name", default="", read_only=True)

    class Meta:
        model = IssueCluster
        fields = [
            "id",
            "title",
            "description",
            "status",
            "category_name",
            "department_name",
            "city",
            "district",
            "state",
            "latitude",
            "longitude",
            "problem_count",
            "total_support_count",
            "unique_reporter_count",
            "aggregate_label",
            "review_required",
            "created_at",
        ]


class ClusterListView(ListAPIView):
    serializer_class = ClusterSerializer
    pagination_class = StandardPageNumberPagination
    filterset_fields = ["state", "district", "city", "status"]
    queryset = (
        IssueCluster.objects.filter(status=ClusterStatus.ACTIVE)
        .select_related("category", "department")
        .order_by("-total_support_count", "-problem_count")
    )


class ClusterDetailView(APIView):
    """The cluster plus every original report inside it.

    Listing the members is the point: the aggregate never replaces the
    individual reports, it summarises them.
    """

    def get(self, request: Request, cluster_id: str) -> Response:
        cluster = (
            IssueCluster.objects.select_related("category", "department")
            .filter(public_id=cluster_id)
            .first()
        )
        if cluster is None:
            return error("NOT_FOUND", "Cluster not found.", status=404)

        from jandrishti.modules.problems.api.serializers import ProblemCardSerializer
        from jandrishti.modules.problems.models import Problem

        problems = list(
            Problem.objects.public()
            .with_display_relations()
            .filter(cluster=cluster)
            .order_by("-support_count")[:100]
        )
        return ok(
            {
                **ClusterSerializer(cluster).data,
                "problems": ProblemCardSerializer(
                    problems, many=True, context={"request": request}
                ).data,
            }
        )


class ClusterMergeView(ActorMixin, APIView):
    """Moderator override for what detection got wrong."""

    permission_classes = [IsAuthenticated, IsModerator]

    def post(self, request: Request, cluster_id: str) -> Response:
        from jandrishti.modules.problems.models import Problem

        cluster = IssueCluster.objects.filter(public_id=cluster_id).first()
        problem = Problem.objects.public().filter(public_id=request.data.get("problem_id")).first()
        if cluster is None or problem is None:
            return error("NOT_FOUND", "Cluster or problem not found.", status=404)

        clustering_service.merge_manually(cluster, problem, request.user)

        from jandrishti.modules.audit.application.recorder import record_audit

        record_audit(
            action="cluster.manual_merge",
            actor=request.user,
            target=f"cluster:{cluster.public_id}",
            metadata={"problem": str(problem.public_id)},
        )
        cluster.refresh_from_db()
        return ok(ClusterSerializer(cluster).data)


class ClusterDetachView(ActorMixin, APIView):
    permission_classes = [IsAuthenticated, IsModerator]

    def post(self, request: Request, cluster_id: str) -> Response:
        from jandrishti.modules.problems.models import Problem

        problem = Problem.objects.public().filter(public_id=request.data.get("problem_id")).first()
        if problem is None:
            return error("NOT_FOUND", "Problem not found.", status=404)

        clustering_service.detach(problem)

        from jandrishti.modules.audit.application.recorder import record_audit

        record_audit(
            action="cluster.detach",
            actor=request.user,
            target=f"problem:{problem.public_id}",
            metadata={"cluster": cluster_id},
        )
        return ok({"detached": True})

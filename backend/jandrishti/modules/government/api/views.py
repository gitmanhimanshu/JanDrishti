"""
Government dashboard.

Every queryset here is scoped to the departments the official actually belongs
to. That scoping is applied in `_scoped_problems` and nowhere else, so there is
one place to audit rather than one per endpoint.
"""

from __future__ import annotations

from django.db.models import Count, Q, QuerySet
from django.utils import timezone
from rest_framework import serializers
from rest_framework.generics import ListAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from jandrishti.modules.audit.application.recorder import record_audit
from jandrishti.modules.problems.api.filters import ProblemFilter
from jandrishti.modules.problems.api.serializers import ProblemCardSerializer
from jandrishti.modules.problems.application.use_cases import (
    UpdateProblemStatusCommand,
    UpdateProblemStatusUseCase,
)
from jandrishti.modules.problems.domain.enums import ProblemStatus
from jandrishti.modules.problems.models import Problem
from jandrishti.shared.api.pagination import StandardPageNumberPagination
from jandrishti.shared.api.permissions import IsGovernmentOfficial
from jandrishti.shared.api.response import created, error, ok
from jandrishti.shared.api.views import ActorMixin

from ..models import DepartmentMembership, ProblemAssignment


def department_paths(user) -> list[str]:
    return list(
        DepartmentMembership.objects.filter(user=user, is_active=True).values_list(
            "department__path", flat=True
        )
    )


def scoped_problems(user) -> QuerySet:
    """Problems this official may see and act on.

    Includes the whole subtree of each department they belong to, because a
    department head is responsible for the wings beneath them.
    """
    if getattr(user, "is_superuser", False) or user.role == "ADMIN":
        return Problem.objects.public()

    paths = department_paths(user)
    if not paths:
        return Problem.objects.none()

    condition = Q()
    for path in paths:
        condition |= Q(department__path=path) | Q(department__path__startswith=f"{path}/")
    return Problem.objects.public().filter(condition)


class UpdateStatusSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=ProblemStatus.choices)
    note = serializers.CharField(required=False, allow_blank=True, max_length=3000)


class AssignSerializer(serializers.Serializer):
    assignee_id = serializers.UUIDField()
    note = serializers.CharField(required=False, allow_blank=True, max_length=500)


class DashboardSummaryView(ActorMixin, APIView):
    """Counts an official needs on landing: workload, urgency, what is stale."""

    permission_classes = [IsAuthenticated, IsGovernmentOfficial]

    def get(self, request: Request) -> Response:
        queryset = scoped_problems(request.user)
        stale_cutoff = timezone.now() - timezone.timedelta(days=14)

        summary = queryset.aggregate(
            total=Count("id"),
            open=Count("id", filter=Q(status__in=ProblemStatus.open_statuses())),
            unacknowledged=Count(
                "id",
                filter=Q(status__in=[ProblemStatus.DEPARTMENT_ASSIGNED, ProblemStatus.SUBMITTED]),
            ),
            in_progress=Count("id", filter=Q(status__in=ProblemStatus.in_progress_statuses())),
            resolved=Count("id", filter=Q(status=ProblemStatus.RESOLVED)),
            critical=Count(
                "id",
                filter=Q(priority="CRITICAL", status__in=ProblemStatus.open_statuses()),
            ),
            stale=Count(
                "id",
                filter=Q(
                    status__in=ProblemStatus.open_statuses(),
                    last_status_change_at__lt=stale_cutoff,
                ),
            ),
        )
        by_status = list(queryset.values("status").annotate(count=Count("id")).order_by("-count"))
        assigned_to_me = ProblemAssignment.objects.filter(
            assignee=request.user, is_current=True
        ).count()

        return ok(
            {
                **summary,
                "assigned_to_me": assigned_to_me,
                "by_status": by_status,
                "departments": department_paths(request.user),
            }
        )


class GovernmentProblemListView(ActorMixin, ListAPIView):
    """The department work queue, using the same filters as the public list."""

    permission_classes = [IsAuthenticated, IsGovernmentOfficial]
    serializer_class = ProblemCardSerializer
    pagination_class = StandardPageNumberPagination
    filterset_class = ProblemFilter

    def get_queryset(self):
        queryset = scoped_problems(self.request.user).with_display_relations()
        if self.request.query_params.get("assigned_to_me") == "true":
            queryset = queryset.filter(
                assignments__assignee=self.request.user, assignments__is_current=True
            )
        return queryset.order_by("-priority", "-support_count", "created_at")


class UpdateProblemStatusView(ActorMixin, APIView):
    """Status changes. The use case re-checks role and department scope."""

    permission_classes = [IsAuthenticated, IsGovernmentOfficial]

    def post(self, request: Request, problem_id: str) -> Response:
        serializer = UpdateStatusSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        problem = UpdateProblemStatusUseCase().execute(
            UpdateProblemStatusCommand(
                problem_id=problem_id,
                to_status=serializer.validated_data["status"],
                note=serializer.validated_data.get("note", ""),
                actor=self.get_actor(),
            )
        )
        return ok({"id": str(problem.public_id), "status": problem.status})


class AssignProblemView(ActorMixin, APIView):
    permission_classes = [IsAuthenticated, IsGovernmentOfficial]

    def post(self, request: Request, problem_id: str) -> Response:
        serializer = AssignSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        problem = scoped_problems(request.user).filter(public_id=problem_id).first()
        if problem is None:
            return error("NOT_FOUND", "Problem not found in your departments.", status=404)
        if problem.department_id is None:
            return error("CONFLICT", "Assign this problem to a department first.", status=409)

        from jandrishti.modules.accounts.models import User

        assignee = User.objects.filter(
            pk=serializer.validated_data["assignee_id"], is_active=True
        ).first()
        if assignee is None:
            return error("NOT_FOUND", "That official was not found.", status=404)
        if not DepartmentMembership.objects.filter(
            user=assignee, department_id=problem.department_id, is_active=True
        ).exists():
            return error(
                "VALIDATION_ERROR",
                "That person is not a member of the department this problem belongs to.",
                status=400,
            )

        # Supersede the previous assignment rather than stacking a second
        # current one -- the unique constraint enforces this too.
        ProblemAssignment.objects.filter(problem=problem, is_current=True).update(is_current=False)
        assignment = ProblemAssignment.objects.create(
            problem=problem,
            assignee=assignee,
            department_id=problem.department_id,
            assigned_by=request.user,
            note=serializer.validated_data.get("note", ""),
        )
        record_audit(
            action="government.problem_assigned",
            actor=request.user,
            target=f"problem:{problem.public_id}",
            metadata={"assignee": str(assignee.id)},
        )
        return created(
            {
                "assignment_id": str(assignment.public_id),
                "assignee": assignee.display_name,
            }
        )

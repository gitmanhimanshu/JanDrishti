"""
Problem endpoints.

Reads are open to everyone. Writes require an account and are authorized on the
server. Views stay thin: they validate input, build a command, call a use case
and serialise the result.
"""

from __future__ import annotations

from django.db.models import F
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.generics import ListAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from jandrishti.modules.media.application.service import MediaService
from jandrishti.modules.media.models import MediaAttachment
from jandrishti.shared.api.pagination import StandardPageNumberPagination
from jandrishti.shared.api.response import created, error, ok
from jandrishti.shared.api.throttling import ScopedActionThrottle
from jandrishti.shared.api.views import ActorMixin

from ..application.use_cases import (
    AddEvidenceCommand,
    AddEvidenceUseCase,
    AddGovernmentResponseCommand,
    AddGovernmentResponseUseCase,
    CreateProblemCommand,
    CreateProblemUseCase,
    SupportProblemCommand,
    SupportProblemUseCase,
    WithdrawSupportCommand,
    WithdrawSupportUseCase,
)
from ..domain.ranking import ranking_registry
from ..models import Problem, ProblemSupport
from .filters import ProblemFilter
from .serializers import (
    AddEvidenceSerializer,
    CreateProblemSerializer,
    GovernmentResponseSerializer,
    GovernmentResponseWriteSerializer,
    ProblemCardSerializer,
    ProblemDetailSerializer,
    SupportSerializer,
)


class ProblemContextMixin(ActorMixin):
    """Builds serializer context in bounded queries, whatever the page size."""

    def media_context(self, problems: list[Problem]) -> dict:
        ids = [problem.id for problem in problems]
        context: dict = {"request": self.request}
        context["media_map"] = MediaService.for_target(MediaAttachment.Target.PROBLEM, ids)
        user = self.request.user
        if user and user.is_authenticated:
            # One query answers "has the viewer supported each of these", rather
            # than one query per card.
            context["supported_ids"] = set(
                ProblemSupport.objects.filter(user=user, problem_id__in=ids).values_list(
                    "problem_id", flat=True
                )
            )
        return context


class ProblemListView(ProblemContextMixin, ListAPIView):
    """GET /api/v1/problems/ -- public, filterable, and tab-ranked."""

    serializer_class = ProblemCardSerializer
    pagination_class = StandardPageNumberPagination
    filter_backends = [DjangoFilterBackend]
    filterset_class = ProblemFilter

    def get_queryset(self):
        queryset = Problem.objects.public().with_display_relations()
        strategy = ranking_registry.get(self.request.query_params.get("tab"))
        return strategy.apply(
            queryset,
            latitude=self.request.query_params.get("lat"),
            longitude=self.request.query_params.get("lng"),
            radius_km=self.request.query_params.get("radius_km"),
        )

    def get_serializer_context(self) -> dict:
        page = getattr(self, "_page_objects", [])
        return self.media_context(list(page))

    def list(self, request: Request, *args, **kwargs) -> Response:
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        self._page_objects = page or []
        serializer = self.get_serializer(self._page_objects, many=True)
        return self.get_paginated_response(serializer.data)


class ProblemTabsView(APIView):
    """The tab list, described by the strategies themselves."""

    def get(self, request: Request) -> Response:
        return ok([strategy.describe() for strategy in ranking_registry.all()])


class ProblemDetailView(ProblemContextMixin, APIView):
    """GET /api/v1/problems/{id} -- public."""

    def get(self, request: Request, problem_id: str) -> Response:
        problem = (
            Problem.objects.public()
            .with_display_relations()
            .prefetch_related("timeline", "government_responses__department")
            .filter(public_id=problem_id)
            .first()
        )
        if problem is None:
            return error("NOT_FOUND", "Problem not found.", status=404)

        # Fire-and-forget counter: an UPDATE avoids the read-modify-write race
        # and never blocks the response on a row lock.
        Problem.objects.filter(pk=problem.pk).update(view_count=F("view_count") + 1)

        context = self.media_context([problem])
        responses = list(problem.government_responses.all())
        context["response_media_map"] = MediaService.for_target(
            MediaAttachment.Target.GOVERNMENT_RESPONSE, [r.id for r in responses]
        )
        return ok(ProblemDetailSerializer(problem, context=context).data)


class ProblemCreateView(ProblemContextMixin, APIView):
    permission_classes = [IsAuthenticated]
    throttle_classes = [ScopedActionThrottle]
    throttle_scope = "create_problem"

    def post(self, request: Request) -> Response:
        serializer = CreateProblemSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        problem = CreateProblemUseCase().execute(
            CreateProblemCommand(
                title=data["title"],
                description=data["description"],
                category_id=str(data["category_id"]) if data.get("category_id") else None,
                department_id=str(data["department_id"]) if data.get("department_id") else None,
                priority=data["priority"],
                address=data.get("address", ""),
                city=data.get("city", ""),
                district=data.get("district", ""),
                state=data.get("state", ""),
                pincode=data.get("pincode", ""),
                latitude=data.get("latitude"),
                longitude=data.get("longitude"),
                media_ids=[str(m) for m in data.get("media_ids", [])],
                is_anonymous_report=data["is_anonymous_report"],
                actor=self.get_actor(),
            )
        )
        return created(ProblemDetailSerializer(problem, context=self.media_context([problem])).data)


class ProblemSupportView(ActorMixin, APIView):
    """POST to support, DELETE to withdraw. Login required (spec 5)."""

    permission_classes = [IsAuthenticated]
    throttle_classes = [ScopedActionThrottle]
    throttle_scope = "support"

    def post(self, request: Request, problem_id: str) -> Response:
        serializer = SupportSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        result = SupportProblemUseCase().execute(
            SupportProblemCommand(
                problem_id=problem_id,
                note=serializer.validated_data.get("note", ""),
                actor=self.get_actor(),
            )
        )
        return ok(
            {
                "support_count": result.support_count,
                "already_supported": result.already_supported,
                "viewer_has_supported": True,
            }
        )

    def delete(self, request: Request, problem_id: str) -> Response:
        result = WithdrawSupportUseCase().execute(
            WithdrawSupportCommand(problem_id=problem_id, actor=self.get_actor())
        )
        return ok({"support_count": result.support_count, "viewer_has_supported": False})


class ProblemEvidenceView(ActorMixin, APIView):
    permission_classes = [IsAuthenticated]
    throttle_classes = [ScopedActionThrottle]
    throttle_scope = "upload"

    def post(self, request: Request, problem_id: str) -> Response:
        serializer = AddEvidenceSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        count = AddEvidenceUseCase().execute(
            AddEvidenceCommand(
                problem_id=problem_id,
                media_ids=[str(m) for m in serializer.validated_data["media_ids"]],
                actor=self.get_actor(),
            )
        )
        return created({"attached": count})


class ProblemResponseView(ActorMixin, APIView):
    """Government responses. Role and department scope checked in the use case."""

    permission_classes = [IsAuthenticated]

    def post(self, request: Request, problem_id: str) -> Response:
        serializer = GovernmentResponseWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        response = AddGovernmentResponseUseCase().execute(
            AddGovernmentResponseCommand(
                problem_id=problem_id,
                message=data["message"],
                kind=data["kind"],
                expected_resolution_date=data.get("expected_resolution_date"),
                reference_number=data.get("reference_number", ""),
                media_ids=[str(m) for m in data.get("media_ids", [])],
                actor=self.get_actor(),
            )
        )
        return created(GovernmentResponseSerializer(response, context={"request": request}).data)

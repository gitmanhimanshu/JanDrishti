"""Experience endpoints. Public to read, account required to contribute."""

from __future__ import annotations

from django.db.models import Count, F
from django_filters import rest_framework as filters
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
    CreateExperienceCommand,
    CreateExperienceUseCase,
    LinkExperienceToProblemCommand,
    LinkExperienceToProblemUseCase,
    SupportExperienceCommand,
    SupportExperienceUseCase,
    WithdrawExperienceSupportCommand,
    WithdrawExperienceSupportUseCase,
)
from ..models import Experience, ExperienceSupport, ExperienceType, ProblemExperienceLink
from .serializers import (
    CreateExperienceSerializer,
    ExperienceCardSerializer,
    ExperienceDetailSerializer,
    LinkProblemSerializer,
)

SORTS = {
    "recent": ("-created_at",),
    "credible": ("-credibility_score", "-support_count"),
    "supported": ("-support_count", "-created_at"),
    "discussed": ("-comment_count", "-created_at"),
}


class ExperienceFilter(filters.FilterSet):
    experience_type = filters.MultipleChoiceFilter(choices=ExperienceType.choices)
    category = filters.CharFilter(field_name="category__public_id")
    state = filters.CharFilter(field_name="state", lookup_expr="iexact")
    verified_authors = filters.BooleanFilter(field_name="author__is_professionally_verified")
    q = filters.CharFilter(method="filter_search")

    class Meta:
        model = Experience
        fields = ["experience_type", "state"]

    def filter_search(self, queryset, name, value):
        from jandrishti.modules.search.application.service import search_service

        return search_service.filter_experiences(queryset, value)


class ExperienceContextMixin(ActorMixin):
    def build_context(self, experiences: list[Experience]) -> dict:
        ids = [experience.id for experience in experiences]
        context: dict = {"request": self.request}
        context["media_map"] = MediaService.for_target(MediaAttachment.Target.EXPERIENCE, ids)
        context["link_counts"] = dict(
            ProblemExperienceLink.objects.filter(experience_id__in=ids)
            .values("experience_id")
            .annotate(total=Count("id"))
            .values_list("experience_id", "total")
        )
        user = self.request.user
        if user and user.is_authenticated:
            context["supported_ids"] = set(
                ExperienceSupport.objects.filter(user=user, experience_id__in=ids).values_list(
                    "experience_id", flat=True
                )
            )
        return context


class ExperienceListView(ExperienceContextMixin, ListAPIView):
    serializer_class = ExperienceCardSerializer
    pagination_class = StandardPageNumberPagination
    filter_backends = [DjangoFilterBackend]
    filterset_class = ExperienceFilter

    def get_queryset(self):
        sort = SORTS.get(self.request.query_params.get("sort", "recent"), SORTS["recent"])
        return Experience.objects.public().with_display_relations().order_by(*sort)

    def get_serializer_context(self) -> dict:
        return self.build_context(list(getattr(self, "_page_objects", [])))

    def list(self, request: Request, *args, **kwargs) -> Response:
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        self._page_objects = page or []
        serializer = self.get_serializer(self._page_objects, many=True)
        return self.get_paginated_response(serializer.data)


class ExperienceDetailView(ExperienceContextMixin, APIView):
    def get(self, request: Request, experience_id: str) -> Response:
        experience = (
            Experience.objects.public()
            .with_display_relations()
            .prefetch_related("problem_links__problem")
            .filter(public_id=experience_id)
            .first()
        )
        if experience is None:
            return error("NOT_FOUND", "Experience not found.", status=404)

        Experience.objects.filter(pk=experience.pk).update(view_count=F("view_count") + 1)
        return ok(
            ExperienceDetailSerializer(experience, context=self.build_context([experience])).data
        )


class ExperienceCreateView(ExperienceContextMixin, APIView):
    permission_classes = [IsAuthenticated]
    throttle_classes = [ScopedActionThrottle]
    throttle_scope = "create_experience"

    def post(self, request: Request) -> Response:
        serializer = CreateExperienceSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        experience = CreateExperienceUseCase().execute(
            CreateExperienceCommand(
                title=data["title"],
                experience_type=data["experience_type"],
                observed_problem=data.get("observed_problem", ""),
                context=data.get("context", ""),
                root_cause=data.get("root_cause", ""),
                personal_experience=data["personal_experience"],
                recommendation=data["recommendation"],
                implementation=data.get("implementation", ""),
                expected_impact=data.get("expected_impact", ""),
                challenges=data.get("challenges", ""),
                cost_implications=data.get("cost_implications", ""),
                category_id=str(data["category_id"]) if data.get("category_id") else None,
                department_id=str(data["department_id"]) if data.get("department_id") else None,
                state=data.get("state", ""),
                district=data.get("district", ""),
                city=data.get("city", ""),
                media_ids=[str(m) for m in data.get("media_ids", [])],
                related_problem_ids=[str(p) for p in data.get("related_problem_ids", [])],
                actor=self.get_actor(),
            )
        )
        return created(
            ExperienceDetailSerializer(experience, context=self.build_context([experience])).data
        )


class ExperienceSupportView(ActorMixin, APIView):
    permission_classes = [IsAuthenticated]
    throttle_classes = [ScopedActionThrottle]
    throttle_scope = "support"

    def post(self, request: Request, experience_id: str) -> Response:
        result = SupportExperienceUseCase().execute(
            SupportExperienceCommand(experience_id=experience_id, actor=self.get_actor())
        )
        return ok(
            {
                "support_count": result.support_count,
                "already_supported": result.already_supported,
                "viewer_has_supported": True,
            }
        )

    def delete(self, request: Request, experience_id: str) -> Response:
        result = WithdrawExperienceSupportUseCase().execute(
            WithdrawExperienceSupportCommand(experience_id=experience_id, actor=self.get_actor())
        )
        return ok({"support_count": result.support_count, "viewer_has_supported": False})


class ExperienceLinkProblemView(ActorMixin, APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request: Request, experience_id: str) -> Response:
        serializer = LinkProblemSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        LinkExperienceToProblemUseCase().execute(
            LinkExperienceToProblemCommand(
                experience_id=experience_id,
                problem_id=str(serializer.validated_data["problem_id"]),
                relevance_note=serializer.validated_data.get("relevance_note", ""),
                actor=self.get_actor(),
            )
        )
        return created({"linked": True})


class ProblemRelatedExperiencesView(ExperienceContextMixin, APIView):
    """Experiences attached to a problem -- rendered on the problem page."""

    def get(self, request: Request, problem_id: str) -> Response:
        experiences = list(
            Experience.objects.public()
            .with_display_relations()
            .filter(problem_links__problem__public_id=problem_id)
            .order_by("-credibility_score")[:20]
        )
        return ok(
            ExperienceCardSerializer(
                experiences, many=True, context=self.build_context(experiences)
            ).data
        )

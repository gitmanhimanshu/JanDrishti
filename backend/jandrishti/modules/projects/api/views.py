"""Project endpoints: public read, government/admin write."""

from __future__ import annotations

from django.db.models import F
from rest_framework import serializers
from rest_framework.generics import ListAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from jandrishti.modules.audit.application.recorder import record_audit
from jandrishti.modules.media.api.views import MediaSerializer
from jandrishti.modules.media.application.service import MediaService
from jandrishti.modules.media.models import MediaAttachment
from jandrishti.shared.api.pagination import StandardPageNumberPagination
from jandrishti.shared.api.permissions import IsGovernmentOfficial
from jandrishti.shared.api.response import created, error, ok
from jandrishti.shared.api.views import ActorMixin
from jandrishti.shared.domain.exceptions import ValidationError as DomainValidationError

from ..models import Project, ProjectMilestone, ProjectStatus, ProjectUpdate, project_lifecycle


class MilestoneSerializer(serializers.ModelSerializer):
    id = serializers.UUIDField(source="public_id", read_only=True)
    is_complete = serializers.BooleanField(read_only=True)

    class Meta:
        model = ProjectMilestone
        fields = [
            "id",
            "title",
            "description",
            "display_order",
            "target_date",
            "completed_at",
            "is_complete",
            "evidence_required",
        ]


class ProjectUpdateSerializer(serializers.ModelSerializer):
    id = serializers.UUIDField(source="public_id", read_only=True)
    author_name = serializers.CharField(source="author.display_name", default="", read_only=True)
    media = serializers.SerializerMethodField()

    class Meta:
        model = ProjectUpdate
        fields = [
            "id",
            "title",
            "body",
            "progress_percent",
            "author_name",
            "media",
            "created_at",
        ]

    def get_media(self, obj: ProjectUpdate) -> list[dict]:
        media_map = self.context.get("update_media_map") or {}
        return MediaSerializer(media_map.get(obj.id, []), many=True).data


class ProjectSerializer(serializers.ModelSerializer):
    id = serializers.UUIDField(source="public_id", read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    problem_id = serializers.UUIDField(source="problem.public_id", default=None, read_only=True)
    department_name = serializers.CharField(source="department.name", default="", read_only=True)

    class Meta:
        model = Project
        fields = [
            "id",
            "title",
            "description",
            "status",
            "status_display",
            "problem_id",
            "department_name",
            "target_amount",
            "start_date",
            "expected_end_date",
            "actual_end_date",
            "progress_percent",
            "update_count",
            "state",
            "district",
            "city",
            "created_at",
        ]


class ProjectDetailSerializer(ProjectSerializer):
    milestones = MilestoneSerializer(many=True, read_only=True)
    updates = serializers.SerializerMethodField()
    funding = serializers.SerializerMethodField()

    class Meta(ProjectSerializer.Meta):
        fields = [*ProjectSerializer.Meta.fields, "milestones", "updates", "funding"]

    def get_updates(self, obj: Project) -> list[dict]:
        updates = list(obj.updates.select_related("author")[:50])
        context = dict(self.context)
        context["update_media_map"] = MediaService.for_target(
            MediaAttachment.Target.PROJECT_UPDATE, [u.id for u in updates]
        )
        return ProjectUpdateSerializer(updates, many=True, context=context).data

    def get_funding(self, obj: Project) -> dict | None:
        """Public money summary: target, collected, spent, remaining (spec 36)."""
        campaign = obj.campaigns.order_by("-created_at").first()
        if campaign is None:
            return None
        return {
            "campaign_id": str(campaign.public_id),
            "status": campaign.status,
            **campaign.public_summary,
        }


class CreateProjectSerializer(serializers.Serializer):
    title = serializers.CharField(min_length=8, max_length=200)
    description = serializers.CharField(min_length=30, max_length=8000)
    problem_id = serializers.UUIDField(required=False, allow_null=True)
    target_amount = serializers.DecimalField(
        max_digits=14, decimal_places=2, required=False, default=0
    )
    start_date = serializers.DateField(required=False, allow_null=True)
    expected_end_date = serializers.DateField(required=False, allow_null=True)
    milestones = serializers.ListField(
        child=serializers.DictField(), required=False, default=list, max_length=25
    )


class ProjectUpdateWriteSerializer(serializers.Serializer):
    title = serializers.CharField(min_length=5, max_length=200)
    body = serializers.CharField(min_length=10, max_length=5000)
    progress_percent = serializers.IntegerField(
        required=False, allow_null=True, min_value=0, max_value=100
    )
    milestone_id = serializers.UUIDField(required=False, allow_null=True)
    media_ids = serializers.ListField(
        child=serializers.UUIDField(), required=False, default=list, max_length=20
    )


class ProjectListView(ListAPIView):
    serializer_class = ProjectSerializer
    pagination_class = StandardPageNumberPagination
    filterset_fields = ["status", "state", "district", "city"]
    queryset = Project.objects.select_related("problem", "department").order_by("-created_at")


class ProjectDetailView(APIView):
    def get(self, request: Request, project_id: str) -> Response:
        project = (
            Project.objects.select_related("problem", "department")
            .prefetch_related("milestones", "campaigns")
            .filter(public_id=project_id)
            .first()
        )
        if project is None:
            return error("NOT_FOUND", "Project not found.", status=404)
        return ok(ProjectDetailSerializer(project, context={"request": request}).data)


class ProjectCreateView(ActorMixin, APIView):
    permission_classes = [IsAuthenticated, IsGovernmentOfficial]

    def post(self, request: Request) -> Response:
        serializer = CreateProjectSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        problem = None
        if data.get("problem_id"):
            from jandrishti.modules.problems.models import Problem, ProblemTimelineEvent

            problem = Problem.objects.public().filter(public_id=data["problem_id"]).first()
            if problem is None:
                return error("NOT_FOUND", "Problem not found.", status=404)

        project = Project.objects.create(
            title=data["title"],
            description=data["description"],
            problem=problem,
            cluster=problem.cluster if problem else None,
            created_by=request.user,
            department=problem.department if problem else None,
            target_amount=data.get("target_amount") or 0,
            start_date=data.get("start_date"),
            expected_end_date=data.get("expected_end_date"),
            state=problem.state if problem else "",
            district=problem.district if problem else "",
            city=problem.city if problem else "",
        )

        ProjectMilestone.objects.bulk_create(
            [
                ProjectMilestone(
                    project=project,
                    title=str(m.get("title", ""))[:200],
                    description=str(m.get("description", ""))[:2000],
                    display_order=index,
                    target_date=m.get("target_date") or None,
                )
                for index, m in enumerate(data.get("milestones", []))
                if m.get("title")
            ]
        )

        if problem:
            from jandrishti.modules.problems.models import ProblemTimelineEvent

            ProblemTimelineEvent.objects.create(
                problem=problem,
                kind=ProblemTimelineEvent.Kind.PROJECT_LINKED,
                title=f"Project started: {project.title}",
                actor=request.user,
                actor_label=project.department.name if project.department else "Government",
                metadata={"project_id": str(project.public_id)},
            )

        record_audit(
            action="project.created",
            actor=request.user,
            target=f"project:{project.public_id}",
            metadata={"problem": str(problem.public_id) if problem else None},
        )
        return created(ProjectDetailSerializer(project, context={"request": request}).data)


class ProjectUpdateView(ActorMixin, APIView):
    """Post a progress update, with proof."""

    permission_classes = [IsAuthenticated, IsGovernmentOfficial]

    def post(self, request: Request, project_id: str) -> Response:
        serializer = ProjectUpdateWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        project = Project.objects.filter(public_id=project_id).first()
        if project is None:
            return error("NOT_FOUND", "Project not found.", status=404)

        milestone = None
        if data.get("milestone_id"):
            milestone = ProjectMilestone.objects.filter(
                public_id=data["milestone_id"], project=project
            ).first()

        update = ProjectUpdate.objects.create(
            project=project,
            milestone=milestone,
            author=request.user,
            title=data["title"],
            body=data["body"],
            progress_percent=data.get("progress_percent"),
        )
        if data.get("media_ids"):
            count = MediaService().attach(
                [str(m) for m in data["media_ids"]],
                target_type=MediaAttachment.Target.PROJECT_UPDATE,
                target_id=update.id,
                owner=request.user,
            )
            ProjectUpdate.objects.filter(pk=update.pk).update(media_count=count)

        fields = {"update_count": F("update_count") + 1}
        if data.get("progress_percent") is not None:
            fields["progress_percent"] = data["progress_percent"]
        Project.objects.filter(pk=project.pk).update(**fields)

        if milestone and data.get("progress_percent") == 100:
            from django.utils import timezone

            milestone.completed_at = timezone.now()
            milestone.save(update_fields=["completed_at", "updated_at"])

        return created(ProjectUpdateSerializer(update, context={"request": request}).data)


class ProjectStatusView(ActorMixin, APIView):
    permission_classes = [IsAuthenticated, IsGovernmentOfficial]

    def post(self, request: Request, project_id: str) -> Response:
        target = request.data.get("status")
        if target not in ProjectStatus.values:
            return error("VALIDATION_ERROR", "Unknown project status.", status=400)

        project = Project.objects.filter(public_id=project_id).first()
        if project is None:
            return error("NOT_FOUND", "Project not found.", status=404)

        # The state machine raises a DomainError, which the exception handler
        # turns into a 409 with the allowed transitions listed.
        project_lifecycle.assert_can(project.status, target)

        # Claiming completion without any evidence is refused: proof of work is
        # the point of this module (spec 34).
        if target == ProjectStatus.COMPLETED:
            has_evidence = MediaAttachment.objects.filter(
                target_type=MediaAttachment.Target.PROJECT_UPDATE,
                target_id__in=project.updates.values_list("id", flat=True),
            ).exists()
            if not has_evidence:
                raise DomainValidationError(
                    "Post at least one update with photographic evidence before marking "
                    "this project complete."
                )

        previous = project.status
        project.status = target
        project.save(update_fields=["status", "updated_at"])
        record_audit(
            action="project.status_changed",
            actor=request.user,
            target=f"project:{project.public_id}",
            metadata={"from": previous, "to": target},
        )
        return ok({"status": project.status})

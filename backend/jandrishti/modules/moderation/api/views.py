"""Moderation endpoints: file a report, work the queue."""

from __future__ import annotations

from django.utils import timezone
from rest_framework import serializers
from rest_framework.generics import ListAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from jandrishti.modules.audit.application.recorder import record_audit
from jandrishti.shared.api.pagination import StandardPageNumberPagination
from jandrishti.shared.api.permissions import IsModerator
from jandrishti.shared.api.response import created, error, ok
from jandrishti.shared.api.throttling import ScopedActionThrottle
from jandrishti.shared.api.views import ActorMixin

from ..models import ContentReport, ReportReason, ReportStatus

# Reports about serious allegations are queued higher, so a human sees them
# sooner. Priority is triage, never a verdict.
SEVERITY = {
    ReportReason.HARASSMENT: 4,
    ReportReason.HATE_SPEECH: 4,
    ReportReason.PRIVACY: 4,
    ReportReason.UNVERIFIED_ALLEGATION: 3,
    ReportReason.INAPPROPRIATE_MEDIA: 3,
    ReportReason.MISLEADING: 2,
    ReportReason.SPAM: 1,
    ReportReason.DUPLICATE: 1,
    ReportReason.OTHER: 1,
}


def resolve_target(target_type: str, public_id: str):
    if target_type == ContentReport.Target.PROBLEM:
        from jandrishti.modules.problems.models import Problem

        return Problem.objects.public().filter(public_id=public_id).first()
    if target_type == ContentReport.Target.EXPERIENCE:
        from jandrishti.modules.experience.models import Experience

        return Experience.objects.public().filter(public_id=public_id).first()
    if target_type == ContentReport.Target.COMMENT:
        from jandrishti.modules.comments.models import Comment

        return Comment.objects.visible().filter(public_id=public_id).first()
    if target_type == ContentReport.Target.MEDIA:
        from jandrishti.modules.media.models import Media

        return Media.objects.filter(public_id=public_id).first()
    if target_type == ContentReport.Target.USER:
        from jandrishti.modules.accounts.models import User

        return User.objects.filter(pk=public_id).first()
    return None


class CreateReportSerializer(serializers.Serializer):
    target_type = serializers.ChoiceField(choices=ContentReport.Target.choices)
    target_id = serializers.CharField(max_length=64)
    reason = serializers.ChoiceField(choices=ReportReason.choices)
    detail = serializers.CharField(required=False, allow_blank=True, max_length=2000)


class ReportSerializer(serializers.ModelSerializer):
    id = serializers.UUIDField(source="public_id", read_only=True)
    reporter_name = serializers.CharField(
        source="reporter.display_name", default="", read_only=True
    )

    class Meta:
        model = ContentReport
        fields = [
            "id",
            "target_type",
            "target_public_id",
            "reason",
            "detail",
            "status",
            "severity",
            "reporter_name",
            "resolution_note",
            "resolved_at",
            "created_at",
        ]


class ResolveSerializer(serializers.Serializer):
    status = serializers.ChoiceField(
        choices=[ReportStatus.ACTION_TAKEN, ReportStatus.DISMISSED, ReportStatus.UNDER_REVIEW]
    )
    note = serializers.CharField(required=False, allow_blank=True, max_length=500)


class ReportContentView(ActorMixin, APIView):
    permission_classes = [IsAuthenticated]
    throttle_classes = [ScopedActionThrottle]
    throttle_scope = "report"

    def post(self, request: Request) -> Response:
        serializer = CreateReportSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        target = resolve_target(data["target_type"], data["target_id"])
        if target is None:
            return error("NOT_FOUND", "That content was not found.", status=404)

        report, was_created = ContentReport.objects.get_or_create(
            reporter=request.user,
            target_type=data["target_type"],
            target_id=target.id,
            status=ReportStatus.OPEN,
            defaults={
                "target_public_id": getattr(target, "public_id", None) or target.pk,
                "reason": data["reason"],
                "detail": data.get("detail", ""),
                "severity": SEVERITY.get(data["reason"], 1),
            },
        )
        return created(
            {
                "id": str(report.public_id),
                "already_reported": not was_created,
                "message": "Thank you. A moderator will review this.",
            }
        )


class ModerationQueueView(ListAPIView):
    permission_classes = [IsAuthenticated, IsModerator]
    serializer_class = ReportSerializer
    pagination_class = StandardPageNumberPagination
    filterset_fields = ["status", "target_type", "reason"]
    queryset = (
        ContentReport.objects.select_related("reporter")
        .filter(status__in=[ReportStatus.OPEN, ReportStatus.UNDER_REVIEW])
        .order_by("-severity", "created_at")
    )


class ResolveReportView(ActorMixin, APIView):
    permission_classes = [IsAuthenticated, IsModerator]

    def post(self, request: Request, report_id: str) -> Response:
        serializer = ResolveSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        report = ContentReport.objects.filter(public_id=report_id).first()
        if report is None:
            return error("NOT_FOUND", "Report not found.", status=404)

        report.status = serializer.validated_data["status"]
        report.resolution_note = serializer.validated_data.get("note", "")
        if report.status in {ReportStatus.ACTION_TAKEN, ReportStatus.DISMISSED}:
            report.resolved_by = request.user
            report.resolved_at = timezone.now()
        report.save()

        record_audit(
            action="moderation.report_resolved",
            actor=request.user,
            target=f"report:{report.public_id}",
            metadata={"status": report.status, "reason": report.reason},
        )
        return ok(ReportSerializer(report).data)

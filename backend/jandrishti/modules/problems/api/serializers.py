"""Problem API contracts."""

from __future__ import annotations

from rest_framework import serializers

from jandrishti.modules.accounts.api.serializers import PublicUserSerializer
from jandrishti.modules.media.api.views import MediaSerializer

from ..domain.enums import ProblemPriority, ProblemStatus
from ..models import GovernmentResponse, Problem, ProblemTimelineEvent


class ProblemLocationSerializer(serializers.Serializer):
    address = serializers.CharField(allow_blank=True)
    city = serializers.CharField(allow_blank=True)
    district = serializers.CharField(allow_blank=True)
    state = serializers.CharField(allow_blank=True)
    pincode = serializers.CharField(allow_blank=True)
    latitude = serializers.FloatField(allow_null=True)
    longitude = serializers.FloatField(allow_null=True)


class ProblemCardSerializer(serializers.ModelSerializer):
    """The list/card projection. Deliberately lean -- lists are hot."""

    id = serializers.UUIDField(source="public_id", read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    priority_display = serializers.CharField(source="get_priority_display", read_only=True)
    category = serializers.SerializerMethodField()
    department = serializers.SerializerMethodField()
    location = serializers.SerializerMethodField()
    cover_image = serializers.SerializerMethodField()
    reporter = serializers.SerializerMethodField()
    viewer_has_supported = serializers.SerializerMethodField()
    cluster_id = serializers.UUIDField(source="cluster.public_id", default=None, read_only=True)

    class Meta:
        model = Problem
        fields = [
            "id",
            "title",
            "slug",
            "status",
            "status_display",
            "priority",
            "priority_display",
            "category",
            "department",
            "location",
            "support_count",
            "report_count",
            "comment_count",
            "evidence_count",
            "cover_image",
            "reporter",
            "viewer_has_supported",
            "cluster_id",
            "created_at",
            "last_activity_at",
            "last_status_change_at",
            "resolved_at",
        ]

    def get_category(self, obj: Problem) -> dict | None:
        if not obj.category:
            return None
        return {
            "id": str(obj.category.public_id),
            "name": obj.category.name,
            "path": obj.category.path,
        }

    def get_department(self, obj: Problem) -> dict | None:
        if not obj.department:
            return None
        return {"id": str(obj.department.public_id), "name": obj.department.name}

    def get_location(self, obj: Problem) -> dict:
        return {
            "city": obj.city,
            "district": obj.district,
            "state": obj.state,
            "latitude": obj.latitude,
            "longitude": obj.longitude,
            "display": ", ".join(p for p in (obj.city, obj.district, obj.state) if p),
        }

    def get_cover_image(self, obj: Problem) -> dict | None:
        media_map = self.context.get("media_map") or {}
        items = media_map.get(obj.id) or []
        image = next((m for m in items if m.media_type == "IMAGE"), None)
        if image is None:
            return None
        return {"url": image.thumbnail_url or image.url, "verified": image.is_verified}

    def get_reporter(self, obj: Problem) -> dict | None:
        """Anonymous reports withhold the name, not the accountability.

        The account is still on the row for moderation and audit; it simply is
        not published.
        """
        if obj.is_anonymous_report or not obj.reporter:
            return {"display_name": "Citizen", "is_anonymous": True}
        return {**PublicUserSerializer(obj.reporter).data, "is_anonymous": False}

    def get_viewer_has_supported(self, obj: Problem) -> bool:
        return obj.id in (self.context.get("supported_ids") or set())


class TimelineEventSerializer(serializers.ModelSerializer):
    id = serializers.UUIDField(source="public_id", read_only=True)
    kind_display = serializers.CharField(source="get_kind_display", read_only=True)

    class Meta:
        model = ProblemTimelineEvent
        fields = [
            "id",
            "kind",
            "kind_display",
            "title",
            "description",
            "from_status",
            "to_status",
            "actor_label",
            "metadata",
            "created_at",
        ]


class GovernmentResponseSerializer(serializers.ModelSerializer):
    id = serializers.UUIDField(source="public_id", read_only=True)
    kind_display = serializers.CharField(source="get_kind_display", read_only=True)
    department_name = serializers.CharField(source="department.name", default="", read_only=True)
    media = serializers.SerializerMethodField()

    class Meta:
        model = GovernmentResponse
        fields = [
            "id",
            "kind",
            "kind_display",
            "message",
            "department_name",
            "expected_resolution_date",
            "reference_number",
            "media",
            "created_at",
        ]

    def get_media(self, obj: GovernmentResponse) -> list[dict]:
        media_map = self.context.get("response_media_map") or {}
        return MediaSerializer(media_map.get(obj.id, []), many=True).data


class ProblemDetailSerializer(ProblemCardSerializer):
    description = serializers.CharField(read_only=True)
    media = serializers.SerializerMethodField()
    timeline = serializers.SerializerMethodField()
    government_responses = serializers.SerializerMethodField()
    allowed_transitions = serializers.SerializerMethodField()
    cluster = serializers.SerializerMethodField()
    days_open = serializers.IntegerField(read_only=True)

    class Meta(ProblemCardSerializer.Meta):
        fields = [
            *ProblemCardSerializer.Meta.fields,
            "description",
            "media",
            "timeline",
            "government_responses",
            "allowed_transitions",
            "cluster",
            "days_open",
            "closure_reason",
            "view_count",
        ]

    def get_media(self, obj: Problem) -> list[dict]:
        media_map = self.context.get("media_map") or {}
        return MediaSerializer(media_map.get(obj.id, []), many=True).data

    def get_timeline(self, obj: Problem) -> list[dict]:
        return TimelineEventSerializer(obj.timeline.all(), many=True).data

    def get_government_responses(self, obj: Problem) -> list[dict]:
        return GovernmentResponseSerializer(
            obj.government_responses.all(), many=True, context=self.context
        ).data

    def get_allowed_transitions(self, obj: Problem) -> list[str]:
        """What *this* viewer could legally do next.

        Purely a UI convenience -- the server re-checks on every attempt.
        """
        request = self.context.get("request")
        user = getattr(request, "user", None)
        if not (
            (user and user.is_authenticated and user.is_staff_role)
            or getattr(user, "is_government", False)
        ):
            return []
        from ..domain.lifecycle import GOVERNMENT_STATUSES, MODERATOR_STATUSES, problem_lifecycle

        allowed = problem_lifecycle.allowed_from(obj.status)
        if getattr(user, "is_superuser", False) or user.role == "ADMIN":
            permitted = set(allowed)
        elif user.role == "MODERATOR":
            permitted = set(allowed) & MODERATOR_STATUSES
        else:
            permitted = set(allowed) & GOVERNMENT_STATUSES
        return sorted(permitted)

    def get_cluster(self, obj: Problem) -> dict | None:
        if not obj.cluster:
            return None
        return {
            "id": str(obj.cluster.public_id),
            "title": obj.cluster.title,
            "problem_count": obj.cluster.problem_count,
            "total_support": obj.cluster.total_support_count,
        }


class CreateProblemSerializer(serializers.Serializer):
    """Input validation only. Business rules live in the use case."""

    title = serializers.CharField(min_length=10, max_length=200)
    description = serializers.CharField(min_length=30, max_length=8000)
    category_id = serializers.UUIDField(required=False, allow_null=True)
    department_id = serializers.UUIDField(required=False, allow_null=True)
    priority = serializers.ChoiceField(
        choices=ProblemPriority.choices, default=ProblemPriority.MEDIUM
    )
    address = serializers.CharField(required=False, allow_blank=True, max_length=500)
    city = serializers.CharField(required=False, allow_blank=True, max_length=120)
    district = serializers.CharField(required=False, allow_blank=True, max_length=120)
    state = serializers.CharField(required=False, allow_blank=True, max_length=120)
    pincode = serializers.CharField(required=False, allow_blank=True, max_length=6)
    latitude = serializers.FloatField(required=False, allow_null=True)
    longitude = serializers.FloatField(required=False, allow_null=True)
    media_ids = serializers.ListField(
        child=serializers.UUIDField(), required=False, default=list, max_length=30
    )
    is_anonymous_report = serializers.BooleanField(default=False)

    def validate(self, attrs: dict) -> dict:
        has_coords = attrs.get("latitude") is not None and attrs.get("longitude") is not None
        if not has_coords and not attrs.get("state"):
            raise serializers.ValidationError(
                "Add a location: either a state or GPS coordinates are needed to route this."
            )
        return attrs


class SupportSerializer(serializers.Serializer):
    note = serializers.CharField(required=False, allow_blank=True, max_length=300)


class UpdateStatusSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=ProblemStatus.choices)
    note = serializers.CharField(required=False, allow_blank=True, max_length=3000)


class GovernmentResponseWriteSerializer(serializers.Serializer):
    message = serializers.CharField(min_length=10, max_length=5000)
    kind = serializers.ChoiceField(
        choices=GovernmentResponse.Kind.choices, default=GovernmentResponse.Kind.PROGRESS_UPDATE
    )
    expected_resolution_date = serializers.DateField(required=False, allow_null=True)
    reference_number = serializers.CharField(required=False, allow_blank=True, max_length=80)
    media_ids = serializers.ListField(
        child=serializers.UUIDField(), required=False, default=list, max_length=20
    )


class AddEvidenceSerializer(serializers.Serializer):
    media_ids = serializers.ListField(child=serializers.UUIDField(), min_length=1, max_length=30)

"""Experience API contracts."""

from __future__ import annotations

from rest_framework import serializers

from jandrishti.modules.accounts.api.serializers import PublicUserSerializer
from jandrishti.modules.media.api.views import MediaSerializer

from ..models import Experience, ExperienceType


class ExperienceCardSerializer(serializers.ModelSerializer):
    id = serializers.UUIDField(source="public_id", read_only=True)
    type_display = serializers.CharField(source="get_experience_type_display", read_only=True)
    author = serializers.SerializerMethodField()
    category = serializers.SerializerMethodField()
    related_problem_count = serializers.SerializerMethodField()
    viewer_has_supported = serializers.SerializerMethodField()
    summary = serializers.SerializerMethodField()

    class Meta:
        model = Experience
        fields = [
            "id",
            "title",
            "slug",
            "experience_type",
            "type_display",
            "summary",
            "author",
            "category",
            "state",
            "city",
            "support_count",
            "comment_count",
            "evidence_count",
            "credibility_score",
            "related_problem_count",
            "viewer_has_supported",
            "created_at",
            "last_activity_at",
        ]

    def get_author(self, obj: Experience) -> dict | None:
        return PublicUserSerializer(obj.author).data if obj.author else None

    def get_category(self, obj: Experience) -> dict | None:
        if not obj.category:
            return None
        return {"id": str(obj.category.public_id), "name": obj.category.name}

    def get_related_problem_count(self, obj: Experience) -> int:
        counts = self.context.get("link_counts") or {}
        return counts.get(obj.id, 0)

    def get_viewer_has_supported(self, obj: Experience) -> bool:
        return obj.id in (self.context.get("supported_ids") or set())

    def get_summary(self, obj: Experience) -> str:
        from jandrishti.shared.infrastructure.text import truncate

        return truncate(obj.recommendation or obj.personal_experience, 220)


class ExperienceDetailSerializer(ExperienceCardSerializer):
    media = serializers.SerializerMethodField()
    related_problems = serializers.SerializerMethodField()

    class Meta(ExperienceCardSerializer.Meta):
        fields = [
            *ExperienceCardSerializer.Meta.fields,
            "observed_problem",
            "context",
            "root_cause",
            "personal_experience",
            "recommendation",
            "implementation",
            "expected_impact",
            "challenges",
            "cost_implications",
            "media",
            "related_problems",
            "author_was_verified",
            "view_count",
        ]

    def get_media(self, obj: Experience) -> list[dict]:
        media_map = self.context.get("media_map") or {}
        return MediaSerializer(media_map.get(obj.id, []), many=True).data

    def get_related_problems(self, obj: Experience) -> list[dict]:
        links = obj.problem_links.select_related("problem").all()
        return [
            {
                "id": str(link.problem.public_id),
                "title": link.problem.title,
                "status": link.problem.status,
                "support_count": link.problem.support_count,
                "relevance_note": link.relevance_note,
            }
            for link in links
        ]


class CreateExperienceSerializer(serializers.Serializer):
    title = serializers.CharField(min_length=10, max_length=200)
    experience_type = serializers.ChoiceField(
        choices=ExperienceType.choices, default=ExperienceType.PROFESSIONAL_EXPERIENCE
    )
    observed_problem = serializers.CharField(required=False, allow_blank=True, max_length=4000)
    context = serializers.CharField(required=False, allow_blank=True, max_length=4000)
    root_cause = serializers.CharField(required=False, allow_blank=True, max_length=4000)
    personal_experience = serializers.CharField(min_length=50, max_length=6000)
    recommendation = serializers.CharField(min_length=30, max_length=6000)
    implementation = serializers.CharField(required=False, allow_blank=True, max_length=4000)
    expected_impact = serializers.CharField(required=False, allow_blank=True, max_length=4000)
    challenges = serializers.CharField(required=False, allow_blank=True, max_length=4000)
    cost_implications = serializers.CharField(required=False, allow_blank=True, max_length=2000)
    category_id = serializers.UUIDField(required=False, allow_null=True)
    department_id = serializers.UUIDField(required=False, allow_null=True)
    state = serializers.CharField(required=False, allow_blank=True, max_length=120)
    district = serializers.CharField(required=False, allow_blank=True, max_length=120)
    city = serializers.CharField(required=False, allow_blank=True, max_length=120)
    media_ids = serializers.ListField(
        child=serializers.UUIDField(), required=False, default=list, max_length=20
    )
    related_problem_ids = serializers.ListField(
        child=serializers.UUIDField(), required=False, default=list, max_length=20
    )


class LinkProblemSerializer(serializers.Serializer):
    problem_id = serializers.UUIDField()
    relevance_note = serializers.CharField(required=False, allow_blank=True, max_length=300)

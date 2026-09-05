"""Comment endpoints. Reading is public; writing needs an account."""

from __future__ import annotations

from rest_framework import serializers
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from jandrishti.modules.accounts.api.serializers import PublicUserSerializer
from jandrishti.shared.api.response import created, error, ok
from jandrishti.shared.api.throttling import ScopedActionThrottle
from jandrishti.shared.api.views import ActorMixin

from ..application.use_cases import (
    CreateCommentCommand,
    CreateCommentUseCase,
    DeleteCommentCommand,
    DeleteCommentUseCase,
    ModerateCommentCommand,
    ModerateCommentUseCase,
    resolve_target,
)
from ..models import Comment, CommentTarget, ModerationState


class CommentSerializer(serializers.ModelSerializer):
    id = serializers.UUIDField(source="public_id", read_only=True)
    author = serializers.SerializerMethodField()
    replies = serializers.SerializerMethodField()

    class Meta:
        model = Comment
        fields = [
            "id",
            "body",
            "author",
            "depth",
            "reply_count",
            "replies",
            "edited_at",
            "created_at",
        ]

    def get_author(self, obj: Comment) -> dict | None:
        return PublicUserSerializer(obj.author).data if obj.author else None

    def get_replies(self, obj: Comment) -> list[dict]:
        children = (self.context.get("children_map") or {}).get(obj.id, [])
        return CommentSerializer(children, many=True, context=self.context).data


class CreateCommentSerializer(serializers.Serializer):
    target_type = serializers.ChoiceField(choices=CommentTarget.choices)
    target_id = serializers.UUIDField()
    body = serializers.CharField(min_length=2, max_length=4000)
    parent_id = serializers.UUIDField(required=False, allow_null=True)


class ModerateSerializer(serializers.Serializer):
    state = serializers.ChoiceField(choices=ModerationState.choices)
    note = serializers.CharField(required=False, allow_blank=True, max_length=300)


class CommentThreadView(APIView):
    """The whole visible thread for one target, assembled in two queries.

    Loading a tree by walking parents would be one query per level per comment.
    Instead: fetch the flat set, then build the nesting in memory.
    """

    def get(self, request: Request, target_type: str, target_id: str) -> Response:
        target_type = target_type.upper()
        if target_type not in CommentTarget.values:
            return error("VALIDATION_ERROR", "Unknown comment target.", status=400)

        target = resolve_target(target_type, target_id)
        if target is None:
            return error("NOT_FOUND", "Content not found.", status=404)

        # Capped: a thread with tens of thousands of comments must not be able
        # to turn one page view into an unbounded response.
        comments = list(
            Comment.objects.visible()
            .for_target(target_type, target.id)
            .select_related("author", "author__professional_profile")
            .order_by("created_at")[:500]
        )
        children_map: dict[int, list[Comment]] = {}
        roots: list[Comment] = []
        for comment in comments:
            if comment.parent_id:
                children_map.setdefault(comment.parent_id, []).append(comment)
            else:
                roots.append(comment)

        serializer = CommentSerializer(
            roots, many=True, context={"children_map": children_map, "request": request}
        )
        return ok({"count": len(comments), "comments": serializer.data})


class CommentCreateView(ActorMixin, APIView):
    permission_classes = [IsAuthenticated]
    throttle_classes = [ScopedActionThrottle]
    throttle_scope = "comment"

    def post(self, request: Request) -> Response:
        serializer = CreateCommentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        comment = CreateCommentUseCase().execute(
            CreateCommentCommand(
                target_type=data["target_type"],
                target_id=str(data["target_id"]),
                body=data["body"],
                parent_id=str(data["parent_id"]) if data.get("parent_id") else None,
                actor=self.get_actor(),
            )
        )
        return created(CommentSerializer(comment, context={"request": request}).data)


class CommentDetailView(ActorMixin, APIView):
    permission_classes = [IsAuthenticated]

    def delete(self, request: Request, comment_id: str) -> Response:
        DeleteCommentUseCase().execute(
            DeleteCommentCommand(comment_id=comment_id, actor=self.get_actor())
        )
        return ok({"deleted": True})


class CommentModerateView(ActorMixin, APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request: Request, comment_id: str) -> Response:
        serializer = ModerateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        comment = ModerateCommentUseCase().execute(
            ModerateCommentCommand(
                comment_id=comment_id,
                state=serializer.validated_data["state"],
                note=serializer.validated_data.get("note", ""),
                actor=self.get_actor(),
            )
        )
        return ok({"id": str(comment.public_id), "moderation_state": comment.moderation_state})

"""Comment use cases."""

from __future__ import annotations

from dataclasses import dataclass, field

from django.conf import settings
from django.db.models import F
from django.utils import timezone

from jandrishti.shared.application.use_case import Actor, UseCase
from jandrishti.shared.domain.events import Events, make_event
from jandrishti.shared.domain.exceptions import (
    NotFoundError,
    PermissionDeniedError,
    ValidationError,
)

from ..models import Comment, CommentTarget, ModerationState


def resolve_target(target_type: str, target_public_id: str):
    """Public UUID to internal row, for whichever kind of thing is commented on.

    Comments are attached generically, so this is the single translation point
    -- and the single place that enforces you can only comment on content that
    is actually public.
    """
    if target_type == CommentTarget.PROBLEM:
        from jandrishti.modules.problems.models import Problem

        return Problem.objects.public().filter(public_id=target_public_id).first()
    if target_type == CommentTarget.EXPERIENCE:
        from jandrishti.modules.experience.models import Experience

        return Experience.objects.public().filter(public_id=target_public_id).first()
    if target_type == CommentTarget.PROJECT:
        from jandrishti.modules.projects.models import Project

        return Project.objects.filter(public_id=target_public_id).first()
    return None


def bump_target_comment_count(target_type: str, target_id: int, delta: int = 1) -> None:
    from django.db.models.functions import Greatest

    expression = (
        F("comment_count") + delta if delta > 0 else Greatest(F("comment_count") + delta, 0)
    )
    if target_type == CommentTarget.PROBLEM:
        from jandrishti.modules.problems.models import Problem

        Problem.objects.filter(pk=target_id).update(
            comment_count=expression, last_activity_at=timezone.now()
        )
    elif target_type == CommentTarget.EXPERIENCE:
        from jandrishti.modules.experience.models import Experience

        Experience.objects.filter(pk=target_id).update(
            comment_count=expression, last_activity_at=timezone.now()
        )


@dataclass(slots=True)
class CreateCommentCommand:
    target_type: str
    target_id: str
    body: str
    parent_id: str | None = None
    actor: Actor = field(default_factory=Actor.anonymous)


class CreateCommentUseCase(UseCase[CreateCommentCommand, Comment]):
    def handle(self, request: CreateCommentCommand) -> Comment:
        user = request.actor.require_authenticated()
        if not user.can_interact:
            raise PermissionDeniedError("This account cannot comment at the moment.")

        body = request.body.strip()
        if len(body) < 2:
            raise ValidationError("Write something a little longer.")

        if request.target_type not in CommentTarget.values:
            raise ValidationError("Unknown comment target.")

        target = resolve_target(request.target_type, request.target_id)
        if target is None:
            raise NotFoundError("The content being commented on was not found.")

        parent = None
        depth = 0
        thread_root = None
        if request.parent_id:
            parent = (
                Comment.objects.visible()
                .filter(
                    public_id=request.parent_id,
                    target_type=request.target_type,
                    target_id=target.id,
                )
                .first()
            )
            # Requiring the parent to share the target is what makes a cycle or
            # a cross-thread reply impossible, not merely unlikely.
            if parent is None:
                raise ValidationError("The comment you are replying to is not available.")

            depth = parent.depth + 1
            max_depth = getattr(settings, "COMMENT_MAX_DEPTH", 5)
            if depth > max_depth:
                raise ValidationError(
                    f"Replies can only be nested {max_depth} levels deep. "
                    "Reply to the parent comment instead."
                )
            thread_root = parent.thread_root or parent

        comment = Comment.objects.create(
            target_type=request.target_type,
            target_id=target.id,
            author=user,
            body=body,
            parent=parent,
            thread_root=thread_root,
            depth=depth,
        )
        if parent is not None:
            Comment.objects.filter(pk=parent.pk).update(reply_count=F("reply_count") + 1)
        bump_target_comment_count(request.target_type, target.id, 1)

        self.record(
            make_event(
                Events.COMMENT_CREATED,
                comment_id=str(comment.public_id),
                target_type=request.target_type,
                target_pk=target.id,
                target_public_id=str(target.public_id),
                author_id=str(user.id),
                parent_author_id=str(parent.author_id) if parent and parent.author_id else None,
            )
        )
        return comment


@dataclass(slots=True)
class DeleteCommentCommand:
    comment_id: str
    actor: Actor = field(default_factory=Actor.anonymous)


class DeleteCommentUseCase(UseCase[DeleteCommentCommand, None]):
    """Soft delete, so replies below it do not vanish with their parent."""

    def handle(self, request: DeleteCommentCommand) -> None:
        user = request.actor.require_authenticated()
        comment = Comment.objects.filter(public_id=request.comment_id).first()
        if comment is None:
            raise NotFoundError("Comment not found.")
        if comment.author_id != user.id and not user.is_staff_role:
            raise PermissionDeniedError("You can only delete your own comments.")

        comment.soft_delete()
        bump_target_comment_count(comment.target_type, comment.target_id, -1)
        return None


@dataclass(slots=True)
class ModerateCommentCommand:
    comment_id: str
    state: str
    note: str = ""
    actor: Actor = field(default_factory=Actor.anonymous)


class ModerateCommentUseCase(UseCase[ModerateCommentCommand, Comment]):
    def handle(self, request: ModerateCommentCommand) -> Comment:
        user = request.actor.require_role("MODERATOR", "ADMIN")
        if request.state not in ModerationState.values:
            raise ValidationError("Unknown moderation state.")

        comment = Comment.objects.filter(public_id=request.comment_id).first()
        if comment is None:
            raise NotFoundError("Comment not found.")

        previous = comment.moderation_state
        comment.moderation_state = request.state
        comment.moderation_note = request.note[:300]
        comment.save(update_fields=["moderation_state", "moderation_note", "updated_at"])

        # Hiding a comment removes it from the visible count too, or the number
        # under the post stops matching the comments people can actually see.
        if previous == ModerationState.VISIBLE and request.state != ModerationState.VISIBLE:
            bump_target_comment_count(comment.target_type, comment.target_id, -1)
        elif previous != ModerationState.VISIBLE and request.state == ModerationState.VISIBLE:
            bump_target_comment_count(comment.target_type, comment.target_id, 1)

        from jandrishti.modules.audit.application.recorder import record_audit

        record_audit(
            action="comment.moderated",
            actor=user,
            target=f"comment:{comment.public_id}",
            metadata={"from": previous, "to": request.state, "note": request.note[:200]},
        )
        return comment

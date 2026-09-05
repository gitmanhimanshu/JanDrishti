"""
Threaded comments (spec 25).

Three defences against the classic comment-tree failures:

* `depth` is stored and capped, so nesting cannot grow without bound;
* `thread_root` lets a whole conversation load in one indexed query instead of
  a recursive walk;
* a parent must belong to the same target, which makes a cycle unrepresentable
  rather than merely discouraged.
"""

from __future__ import annotations

from django.conf import settings
from django.db import models

from jandrishti.shared.models import BaseEntity, SoftDeleteModel


class CommentTarget(models.TextChoices):
    PROBLEM = "PROBLEM", "Problem"
    EXPERIENCE = "EXPERIENCE", "Experience"
    PROJECT = "PROJECT", "Project"


class ModerationState(models.TextChoices):
    VISIBLE = "VISIBLE", "Visible"
    FLAGGED = "FLAGGED", "Flagged for review"
    HIDDEN = "HIDDEN", "Hidden by moderator"
    REMOVED = "REMOVED", "Removed"


class CommentQuerySet(models.QuerySet):
    def visible(self) -> CommentQuerySet:
        return self.filter(deleted_at__isnull=True, moderation_state=ModerationState.VISIBLE)

    def for_target(self, target_type: str, target_id: int) -> CommentQuerySet:
        return self.filter(target_type=target_type, target_id=target_id)


class CommentManager(models.Manager.from_queryset(CommentQuerySet)):  # type: ignore[misc]
    def get_queryset(self) -> CommentQuerySet:
        return super().get_queryset().filter(deleted_at__isnull=True)


class Comment(BaseEntity, SoftDeleteModel):
    target_type = models.CharField(max_length=20, choices=CommentTarget.choices, db_index=True)
    target_id = models.BigIntegerField(db_index=True)

    author = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="comments"
    )
    body = models.TextField(max_length=4000)

    parent = models.ForeignKey(
        "self", null=True, blank=True, on_delete=models.CASCADE, related_name="replies"
    )
    # The top-level comment this reply hangs from. Null on a root comment.
    thread_root = models.ForeignKey(
        "self", null=True, blank=True, on_delete=models.CASCADE, related_name="thread_comments"
    )
    depth = models.PositiveSmallIntegerField(default=0)
    reply_count = models.PositiveIntegerField(default=0)

    moderation_state = models.CharField(
        max_length=20,
        choices=ModerationState.choices,
        default=ModerationState.VISIBLE,
        db_index=True,
    )
    moderation_note = models.CharField(max_length=300, blank=True)
    edited_at = models.DateTimeField(null=True, blank=True)

    objects = CommentManager()
    all_objects = models.Manager.from_queryset(CommentQuerySet)()

    class Meta:
        db_table = "comment"
        ordering = ["created_at"]
        indexes = [
            models.Index(fields=["target_type", "target_id", "created_at"]),
            models.Index(fields=["thread_root", "created_at"]),
            models.Index(fields=["author", "-created_at"]),
        ]
        constraints = [
            models.CheckConstraint(condition=models.Q(depth__lte=10), name="ck_comment_max_depth")
        ]

    def __str__(self) -> str:
        return f"comment {self.public_id} on {self.target_type}#{self.target_id}"

    @property
    def is_reply(self) -> bool:
        return self.parent_id is not None

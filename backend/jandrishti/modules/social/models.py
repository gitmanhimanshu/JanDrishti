"""
Bookmarks and follows (spec 26).

Both are generic over target type, so following an author, a problem, an
experience or a project is one table and one code path. Follows are what drive
notifications: a change to a followed object is the trigger.
"""

from __future__ import annotations

from django.conf import settings
from django.db import models
from django.utils import timezone

from jandrishti.shared.models import BaseEntity


class TargetType(models.TextChoices):
    PROBLEM = "PROBLEM", "Problem"
    EXPERIENCE = "EXPERIENCE", "Experience"
    PROJECT = "PROJECT", "Project"
    USER = "USER", "User"
    DEPARTMENT = "DEPARTMENT", "Department"
    CLUSTER = "CLUSTER", "Issue cluster"


class Bookmark(BaseEntity):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="bookmarks"
    )
    target_type = models.CharField(max_length=20, choices=TargetType.choices, db_index=True)
    target_id = models.BigIntegerField(db_index=True)
    # Denormalised so the bookmark list renders without four conditional joins.
    target_title = models.CharField(max_length=250, blank=True)
    target_public_id = models.UUIDField(null=True, blank=True)

    class Meta:
        db_table = "social_bookmark"
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(fields=["user", "target_type", "target_id"], name="uq_bookmark")
        ]
        indexes = [models.Index(fields=["user", "target_type", "-created_at"])]


class Follow(BaseEntity):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="following"
    )
    target_type = models.CharField(max_length=20, choices=TargetType.choices, db_index=True)
    target_id = models.BigIntegerField(db_index=True)
    target_public_id = models.UUIDField(null=True, blank=True)
    target_title = models.CharField(max_length=250, blank=True)
    # Muting keeps the follow but stops the notifications, which is what people
    # actually want from a noisy thread they still care about.
    notifications_enabled = models.BooleanField(default=True)
    last_notified_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "social_follow"
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(fields=["user", "target_type", "target_id"], name="uq_follow")
        ]
        indexes = [
            models.Index(fields=["user", "target_type"]),
            # The notification fan-out query: everyone following this object.
            models.Index(fields=["target_type", "target_id", "notifications_enabled"]),
        ]

    def mark_notified(self) -> None:
        self.last_notified_at = timezone.now()
        self.save(update_fields=["last_notified_at", "updated_at"])

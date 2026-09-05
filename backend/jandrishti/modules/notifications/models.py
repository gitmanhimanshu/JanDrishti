"""Notifications (spec 62)."""

from __future__ import annotations

from django.conf import settings
from django.db import models
from django.utils import timezone

from jandrishti.shared.models import BaseEntity


class NotificationKind(models.TextChoices):
    PROBLEM_STATUS_CHANGED = "PROBLEM_STATUS_CHANGED", "Problem status changed"
    GOVERNMENT_RESPONSE = "GOVERNMENT_RESPONSE", "Government response"
    COMMENT_ON_CONTENT = "COMMENT_ON_CONTENT", "New comment"
    COMMENT_REPLY = "COMMENT_REPLY", "Reply to your comment"
    FOLLOWED_PROBLEM_UPDATED = "FOLLOWED_PROBLEM_UPDATED", "Followed problem updated"
    FOLLOWED_EXPERIENCE_UPDATED = "FOLLOWED_EXPERIENCE_UPDATED", "Followed experience updated"
    PROJECT_UPDATE = "PROJECT_UPDATE", "Project update"
    VERIFICATION_RESULT = "VERIFICATION_RESULT", "Verification result"
    PROBLEM_CLUSTERED = "PROBLEM_CLUSTERED", "Report grouped with similar ones"
    SUPPORT_MILESTONE = "SUPPORT_MILESTONE", "Support milestone reached"


class Notification(BaseEntity):
    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="notifications"
    )
    kind = models.CharField(max_length=40, choices=NotificationKind.choices, db_index=True)
    title = models.CharField(max_length=200)
    body = models.CharField(max_length=500, blank=True)
    # Relative path into the frontend, so the client can route without knowing
    # how each notification kind maps to a page.
    link_path = models.CharField(max_length=300, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    read_at = models.DateTimeField(null=True, blank=True, db_index=True)

    class Meta:
        db_table = "notification"
        ordering = ["-created_at"]
        indexes = [
            # The unread badge query. Partial, because read notifications
            # quickly outnumber unread ones by orders of magnitude.
            models.Index(
                fields=["recipient", "-created_at"],
                condition=models.Q(read_at__isnull=True),
                name="idx_notification_unread",
            ),
            models.Index(fields=["recipient", "-created_at"]),
        ]

    def __str__(self) -> str:
        return f"{self.kind} for {self.recipient_id}"

    def mark_read(self) -> None:
        if self.read_at is None:
            self.read_at = timezone.now()
            self.save(update_fields=["read_at", "updated_at"])

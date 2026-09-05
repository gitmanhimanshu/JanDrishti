"""
Moderation (spec 57).

Reports come from the public; decisions come from people. The one rule encoded
here is that no automated process resolves a report about a serious allegation
-- AI may triage and prioritise, but a human closes it (spec 40, 57).
"""

from __future__ import annotations

from django.conf import settings
from django.db import models

from jandrishti.shared.models import BaseEntity


class ReportReason(models.TextChoices):
    SPAM = "SPAM", "Spam"
    HARASSMENT = "HARASSMENT", "Harassment or abuse"
    HATE_SPEECH = "HATE_SPEECH", "Hate speech"
    MISLEADING = "MISLEADING", "Misleading or false"
    DUPLICATE = "DUPLICATE", "Duplicate content"
    PRIVACY = "PRIVACY", "Exposes private information"
    INAPPROPRIATE_MEDIA = "INAPPROPRIATE_MEDIA", "Inappropriate media"
    UNVERIFIED_ALLEGATION = "UNVERIFIED_ALLEGATION", "Serious allegation without evidence"
    OTHER = "OTHER", "Other"


class ReportStatus(models.TextChoices):
    OPEN = "OPEN", "Open"
    UNDER_REVIEW = "UNDER_REVIEW", "Under review"
    ACTION_TAKEN = "ACTION_TAKEN", "Action taken"
    DISMISSED = "DISMISSED", "Dismissed"


class ContentReport(BaseEntity):
    class Target(models.TextChoices):
        PROBLEM = "PROBLEM", "Problem"
        EXPERIENCE = "EXPERIENCE", "Experience"
        COMMENT = "COMMENT", "Comment"
        MEDIA = "MEDIA", "Media"
        USER = "USER", "User"

    target_type = models.CharField(max_length=20, choices=Target.choices, db_index=True)
    target_id = models.BigIntegerField(db_index=True)
    target_public_id = models.UUIDField(null=True, blank=True)

    reporter = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="filed_reports"
    )
    reason = models.CharField(max_length=30, choices=ReportReason.choices)
    detail = models.TextField(max_length=2000, blank=True)

    status = models.CharField(
        max_length=20, choices=ReportStatus.choices, default=ReportStatus.OPEN, db_index=True
    )
    # Set by triage; used only to order the queue, never to decide an outcome.
    severity = models.PositiveSmallIntegerField(default=1)

    resolved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="resolved_reports",
    )
    resolved_at = models.DateTimeField(null=True, blank=True)
    resolution_note = models.CharField(max_length=500, blank=True)

    class Meta:
        db_table = "moderation_content_report"
        ordering = ["-severity", "created_at"]
        indexes = [
            models.Index(fields=["status", "-severity", "created_at"]),
            models.Index(fields=["target_type", "target_id"]),
        ]
        constraints = [
            # One open report per person per item: brigading should not be able
            # to inflate a queue position.
            models.UniqueConstraint(
                fields=["reporter", "target_type", "target_id"],
                condition=models.Q(status__in=["OPEN", "UNDER_REVIEW"]),
                name="uq_one_open_report_per_reporter",
            )
        ]

    def __str__(self) -> str:
        return f"{self.reason} on {self.target_type}#{self.target_id}"

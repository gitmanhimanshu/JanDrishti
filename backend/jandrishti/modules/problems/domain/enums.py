"""Problem statuses and priorities (spec 33)."""

from __future__ import annotations

from django.db import models


class ProblemStatus(models.TextChoices):
    """The lifecycle a civic problem moves through.

    Two tracks: the main path from SUBMITTED to RESOLVED, and terminal outcomes
    for reports that cannot proceed. Both are public, because a citizen is owed
    an answer either way -- including when the answer is `not our jurisdiction`.
    """

    SUBMITTED = "SUBMITTED", "Submitted"
    UNDER_REVIEW = "UNDER_REVIEW", "Under review"
    VERIFIED = "VERIFIED", "Verified"
    DEPARTMENT_ASSIGNED = "DEPARTMENT_ASSIGNED", "Department assigned"
    ACKNOWLEDGED = "ACKNOWLEDGED", "Acknowledged"
    INSPECTION = "INSPECTION", "Inspection"
    ACTION_PLANNED = "ACTION_PLANNED", "Action planned"
    WORK_STARTED = "WORK_STARTED", "Work started"
    WORK_IN_PROGRESS = "WORK_IN_PROGRESS", "Work in progress"
    COMPLETED = "COMPLETED", "Completed"
    VERIFICATION = "VERIFICATION", "Verification"
    RESOLVED = "RESOLVED", "Resolved"

    # Terminal outcomes.
    REJECTED = "REJECTED", "Rejected"
    DUPLICATE = "DUPLICATE", "Duplicate"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE", "Insufficient evidence"
    OUTSIDE_JURISDICTION = "OUTSIDE_JURISDICTION", "Outside jurisdiction"
    ALREADY_RESOLVED = "ALREADY_RESOLVED", "Already resolved"

    @classmethod
    def open_statuses(cls) -> tuple[str, ...]:
        return (
            cls.SUBMITTED,
            cls.UNDER_REVIEW,
            cls.VERIFIED,
            cls.DEPARTMENT_ASSIGNED,
            cls.ACKNOWLEDGED,
            cls.INSPECTION,
            cls.ACTION_PLANNED,
            cls.WORK_STARTED,
            cls.WORK_IN_PROGRESS,
            cls.COMPLETED,
            cls.VERIFICATION,
        )

    @classmethod
    def closed_statuses(cls) -> tuple[str, ...]:
        return (
            cls.RESOLVED,
            cls.REJECTED,
            cls.DUPLICATE,
            cls.INSUFFICIENT_EVIDENCE,
            cls.OUTSIDE_JURISDICTION,
            cls.ALREADY_RESOLVED,
        )

    @classmethod
    def in_progress_statuses(cls) -> tuple[str, ...]:
        return (cls.WORK_STARTED, cls.WORK_IN_PROGRESS, cls.INSPECTION, cls.ACTION_PLANNED)


class ProblemPriority(models.TextChoices):
    LOW = "LOW", "Low"
    MEDIUM = "MEDIUM", "Medium"
    HIGH = "HIGH", "High"
    CRITICAL = "CRITICAL", "Critical"

    @classmethod
    def weight(cls, value: str) -> int:
        return {cls.LOW: 1, cls.MEDIUM: 2, cls.HIGH: 4, cls.CRITICAL: 8}.get(value, 2)


class ProblemVisibility(models.TextChoices):
    PUBLIC = "PUBLIC", "Public"
    # Held back from public listing pending moderation -- used when a report is
    # flagged, never as a default.
    UNDER_MODERATION = "UNDER_MODERATION", "Under moderation"
    REMOVED = "REMOVED", "Removed"

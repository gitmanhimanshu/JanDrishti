"""
Problems: the civic record at the centre of the platform.

Counter design (spec 18, 49). `support_count` is a denormalised cache of a row
count, never a number the client sends. The authority is the unique constraint
on `problem_supports`; the cached column is only ever moved with an atomic
`F(...) + 1` inside the same transaction as the insert. A read-modify-write of
a Python integer would lose supports under concurrency, which is precisely the
failure the spec calls out.
"""

from __future__ import annotations

from django.conf import settings
from django.db import models
from django.utils import timezone

from jandrishti.shared.models import BaseEntity, LocatedModel, SoftDeleteModel

from .domain.enums import ProblemPriority, ProblemStatus, ProblemVisibility


class ProblemQuerySet(models.QuerySet):
    def public(self) -> ProblemQuerySet:
        """What an anonymous visitor is allowed to see."""
        return self.filter(deleted_at__isnull=True, visibility=ProblemVisibility.PUBLIC)

    def open(self) -> ProblemQuerySet:
        return self.filter(status__in=ProblemStatus.open_statuses())

    def resolved(self) -> ProblemQuerySet:
        return self.filter(status=ProblemStatus.RESOLVED)

    def with_display_relations(self) -> ProblemQuerySet:
        """The joins every card and detail page needs -- the N+1 guard."""
        return self.select_related("reporter", "category", "department", "cluster")


class ProblemManager(models.Manager.from_queryset(ProblemQuerySet)):  # type: ignore[misc]
    def get_queryset(self) -> ProblemQuerySet:
        return super().get_queryset().filter(deleted_at__isnull=True)


class Problem(BaseEntity, SoftDeleteModel, LocatedModel):
    title = models.CharField(max_length=200)
    description = models.TextField(max_length=8000)
    slug = models.SlugField(max_length=220, blank=True)

    reporter = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="reported_problems",
    )
    category = models.ForeignKey(
        "catalog.Category",
        on_delete=models.PROTECT,
        related_name="problems",
        null=True,
        blank=True,
    )
    department = models.ForeignKey(
        "catalog.Department",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="problems",
    )
    cluster = models.ForeignKey(
        "issue_clustering.IssueCluster",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="problems",
    )

    status = models.CharField(
        max_length=30,
        choices=ProblemStatus.choices,
        default=ProblemStatus.SUBMITTED,
        db_index=True,
    )
    priority = models.CharField(
        max_length=20,
        choices=ProblemPriority.choices,
        default=ProblemPriority.MEDIUM,
        db_index=True,
    )
    visibility = models.CharField(
        max_length=20,
        choices=ProblemVisibility.choices,
        default=ProblemVisibility.PUBLIC,
        db_index=True,
    )

    # -- denormalised counters (authority lives in the related tables) -------
    support_count = models.PositiveIntegerField(default=0, db_index=True)
    report_count = models.PositiveIntegerField(default=1, db_index=True)
    comment_count = models.PositiveIntegerField(default=0)
    evidence_count = models.PositiveIntegerField(default=0)
    view_count = models.PositiveBigIntegerField(default=0)
    trend_score = models.FloatField(default=0.0, db_index=True)

    # -- lifecycle timestamps ------------------------------------------------
    last_activity_at = models.DateTimeField(default=timezone.now, db_index=True)
    last_status_change_at = models.DateTimeField(null=True, blank=True, db_index=True)
    acknowledged_at = models.DateTimeField(null=True, blank=True)
    resolved_at = models.DateTimeField(null=True, blank=True)
    closure_reason = models.CharField(max_length=500, blank=True)

    # AI assistance is recorded as a *suggestion*, never as a decision. A human
    # confirms the category and the department (spec 40).
    ai_suggested_category = models.ForeignKey(
        "catalog.Category",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="ai_suggested_problems",
    )
    ai_confidence = models.FloatField(null=True, blank=True)
    ai_summary = models.TextField(max_length=1000, blank=True)

    is_anonymous_report = models.BooleanField(
        default=False,
        help_text="Hide the reporter name publicly. The account is still recorded internally.",
    )

    objects = ProblemManager()
    all_objects = models.Manager.from_queryset(ProblemQuerySet)()

    class Meta:
        db_table = "problem"
        ordering = ["-created_at"]
        indexes = [
            # The Problems page is filter-then-sort; these cover the tabs.
            models.Index(fields=["visibility", "status", "-created_at"]),
            models.Index(fields=["visibility", "-trend_score"]),
            models.Index(fields=["visibility", "-support_count"]),
            models.Index(fields=["state", "district", "status"]),
            models.Index(fields=["category", "status"]),
            models.Index(fields=["department", "status"]),
            models.Index(fields=["latitude", "longitude"]),
            models.Index(fields=["cluster", "-support_count"]),
            # Partial index: the government dashboard only ever queries open
            # issues, and they are a shrinking minority as the archive grows.
            models.Index(
                fields=["department", "priority", "-created_at"],
                condition=models.Q(status__in=ProblemStatus.open_statuses()),
                name="idx_problem_open_by_dept",
            ),
        ]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(latitude__gte=-90, latitude__lte=90)
                | models.Q(latitude__isnull=True),
                name="ck_problem_latitude_range",
            ),
            models.CheckConstraint(
                condition=models.Q(longitude__gte=-180, longitude__lte=180)
                | models.Q(longitude__isnull=True),
                name="ck_problem_longitude_range",
            ),
        ]

    def __str__(self) -> str:
        return self.title

    def save(self, *args, **kwargs):
        if not self.slug:
            from django.utils.text import slugify

            self.slug = slugify(self.title)[:220]
        super().save(*args, **kwargs)

    @property
    def is_open(self) -> bool:
        return self.status in ProblemStatus.open_statuses()

    @property
    def is_resolved(self) -> bool:
        return self.status == ProblemStatus.RESOLVED

    @property
    def days_open(self) -> int:
        end = self.resolved_at or timezone.now()
        return max((end - self.created_at).days, 0)

    @property
    def public_url(self) -> str:
        return f"{settings.FRONTEND_URL}/problems/{self.public_id}"


class ProblemSupport(models.Model):
    """One row per person per problem. The unique constraint is the truth.

    "Support" here means "I face this problem too" -- civic weight, not a social
    like (spec 14). It is deliberately not reversible into a negative signal:
    there is no downvote on somebody else's lived problem.
    """

    problem = models.ForeignKey(Problem, on_delete=models.CASCADE, related_name="supports")
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="problem_supports"
    )
    created_at = models.DateTimeField(default=timezone.now, db_index=True)
    # Optional context: how this person is affected.
    note = models.CharField(max_length=300, blank=True)

    class Meta:
        db_table = "problem_supports"
        constraints = [
            models.UniqueConstraint(fields=["problem", "user"], name="uq_problem_support")
        ]
        indexes = [models.Index(fields=["user", "-created_at"])]

    def __str__(self) -> str:
        return f"{self.user_id} supports {self.problem_id}"


class ProblemTimelineEvent(BaseEntity):
    """The permanent public record of what happened to this problem (spec 34).

    Append-only. Status changes, responses, evidence and project links all land
    here so the timeline reads as one story rather than four disconnected lists.
    """

    class Kind(models.TextChoices):
        REPORTED = "REPORTED", "Reported"
        STATUS_CHANGED = "STATUS_CHANGED", "Status changed"
        DEPARTMENT_ASSIGNED = "DEPARTMENT_ASSIGNED", "Department assigned"
        GOVERNMENT_RESPONSE = "GOVERNMENT_RESPONSE", "Government response"
        EVIDENCE_ADDED = "EVIDENCE_ADDED", "Evidence added"
        EVIDENCE_VERIFIED = "EVIDENCE_VERIFIED", "Evidence verified"
        INSPECTION = "INSPECTION", "Inspection"
        PROGRESS_UPDATE = "PROGRESS_UPDATE", "Progress update"
        PROJECT_LINKED = "PROJECT_LINKED", "Project linked"
        CLUSTERED = "CLUSTERED", "Merged into cluster"
        RESOLVED = "RESOLVED", "Resolved"

    problem = models.ForeignKey(Problem, on_delete=models.CASCADE, related_name="timeline")
    kind = models.CharField(max_length=30, choices=Kind.choices, db_index=True)
    title = models.CharField(max_length=200)
    description = models.TextField(max_length=3000, blank=True)
    from_status = models.CharField(max_length=30, blank=True)
    to_status = models.CharField(max_length=30, blank=True)
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="problem_timeline_entries",
    )
    # Shown publicly as the acting body rather than a named official.
    actor_label = models.CharField(max_length=150, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        db_table = "problem_timeline_event"
        ordering = ["created_at"]
        indexes = [models.Index(fields=["problem", "created_at"])]

    def __str__(self) -> str:
        return f"{self.problem_id}: {self.title}"


class GovernmentResponse(BaseEntity):
    """An official statement on a problem.

    Public and permanent. Responses are attributable to a department and an
    official, and every one of them is audited.
    """

    class Kind(models.TextChoices):
        ACKNOWLEDGEMENT = "ACKNOWLEDGEMENT", "Acknowledgement"
        INSPECTION_REPORT = "INSPECTION_REPORT", "Inspection report"
        ACTION_PLAN = "ACTION_PLAN", "Action plan"
        PROGRESS_UPDATE = "PROGRESS_UPDATE", "Progress update"
        COMPLETION = "COMPLETION", "Completion report"
        CLARIFICATION = "CLARIFICATION", "Clarification"
        REJECTION = "REJECTION", "Rejection"

    problem = models.ForeignKey(
        Problem, on_delete=models.CASCADE, related_name="government_responses"
    )
    department = models.ForeignKey(
        "catalog.Department", on_delete=models.SET_NULL, null=True, related_name="responses"
    )
    official = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="government_responses",
    )
    kind = models.CharField(max_length=30, choices=Kind.choices, default=Kind.PROGRESS_UPDATE)
    message = models.TextField(max_length=5000)
    expected_resolution_date = models.DateField(null=True, blank=True)
    reference_number = models.CharField(max_length=80, blank=True)

    class Meta:
        db_table = "problem_government_response"
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["problem", "-created_at"])]

    def __str__(self) -> str:
        return f"{self.get_kind_display()} on {self.problem_id}"

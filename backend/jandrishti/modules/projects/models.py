"""
Projects and proof of work (spec 35, 34).

A problem can lead to one or more projects; a project carries milestones,
updates and evidence. The point of this module is the last column of the
lifecycle: proof. A project that claims completion without before/after
evidence is visibly a project without evidence.
"""

from __future__ import annotations

from django.conf import settings
from django.db import models

from jandrishti.shared.domain.state_machine import StateMachine
from jandrishti.shared.models import BaseEntity


class ProjectStatus(models.TextChoices):
    PROPOSED = "PROPOSED", "Proposed"
    APPROVED = "APPROVED", "Approved"
    FUNDING = "FUNDING", "Raising funds"
    IN_PROGRESS = "IN_PROGRESS", "In progress"
    COMPLETED = "COMPLETED", "Completed"
    VERIFIED = "VERIFIED", "Verified"
    CANCELLED = "CANCELLED", "Cancelled"
    ON_HOLD = "ON_HOLD", "On hold"


project_lifecycle: StateMachine[str] = StateMachine(
    {
        ProjectStatus.PROPOSED: (ProjectStatus.APPROVED, ProjectStatus.CANCELLED),
        ProjectStatus.APPROVED: (
            ProjectStatus.FUNDING,
            ProjectStatus.IN_PROGRESS,
            ProjectStatus.CANCELLED,
        ),
        ProjectStatus.FUNDING: (
            ProjectStatus.IN_PROGRESS,
            ProjectStatus.ON_HOLD,
            ProjectStatus.CANCELLED,
        ),
        ProjectStatus.IN_PROGRESS: (
            ProjectStatus.COMPLETED,
            ProjectStatus.ON_HOLD,
            ProjectStatus.CANCELLED,
        ),
        ProjectStatus.ON_HOLD: (ProjectStatus.IN_PROGRESS, ProjectStatus.CANCELLED),
        # Completion is a claim; VERIFIED is the claim checked against evidence.
        ProjectStatus.COMPLETED: (ProjectStatus.VERIFIED, ProjectStatus.IN_PROGRESS),
        ProjectStatus.VERIFIED: (),
        ProjectStatus.CANCELLED: (),
    },
    terminal=(ProjectStatus.VERIFIED, ProjectStatus.CANCELLED),
    name="project",
)


class Project(BaseEntity):
    problem = models.ForeignKey(
        "problems.Problem",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="projects",
    )
    cluster = models.ForeignKey(
        "issue_clustering.IssueCluster",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="projects",
    )
    title = models.CharField(max_length=200)
    description = models.TextField(max_length=8000)
    status = models.CharField(
        max_length=20, choices=ProjectStatus.choices, default=ProjectStatus.PROPOSED, db_index=True
    )

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="projects"
    )
    department = models.ForeignKey(
        "catalog.Department",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="projects",
    )

    target_amount = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    start_date = models.DateField(null=True, blank=True)
    expected_end_date = models.DateField(null=True, blank=True)
    actual_end_date = models.DateField(null=True, blank=True)

    state = models.CharField(max_length=120, blank=True, db_index=True)
    district = models.CharField(max_length=120, blank=True)
    city = models.CharField(max_length=120, blank=True)

    progress_percent = models.PositiveSmallIntegerField(default=0)
    update_count = models.PositiveIntegerField(default=0)
    comment_count = models.PositiveIntegerField(default=0)

    class Meta:
        db_table = "project"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["status", "-created_at"]),
            models.Index(fields=["problem", "status"]),
            models.Index(fields=["state", "status"]),
        ]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(progress_percent__lte=100), name="ck_project_progress_max"
            )
        ]

    def __str__(self) -> str:
        return self.title


class ProjectMilestone(BaseEntity):
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="milestones")
    title = models.CharField(max_length=200)
    description = models.TextField(max_length=2000, blank=True)
    display_order = models.PositiveSmallIntegerField(default=0)
    target_date = models.DateField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    # A milestone marked complete without evidence is visibly unproven.
    evidence_required = models.BooleanField(default=True)

    class Meta:
        db_table = "project_milestone"
        ordering = ["display_order", "created_at"]
        indexes = [models.Index(fields=["project", "display_order"])]

    def __str__(self) -> str:
        return f"{self.project_id}: {self.title}"

    @property
    def is_complete(self) -> bool:
        return self.completed_at is not None


class ProjectUpdate(BaseEntity):
    """A dated progress note, optionally carrying before/during/after media."""

    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="updates")
    milestone = models.ForeignKey(
        ProjectMilestone, on_delete=models.SET_NULL, null=True, blank=True, related_name="updates"
    )
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="project_updates",
    )
    title = models.CharField(max_length=200)
    body = models.TextField(max_length=5000)
    progress_percent = models.PositiveSmallIntegerField(null=True, blank=True)
    media_count = models.PositiveIntegerField(default=0)

    class Meta:
        db_table = "project_update"
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["project", "-created_at"])]

    def __str__(self) -> str:
        return self.title

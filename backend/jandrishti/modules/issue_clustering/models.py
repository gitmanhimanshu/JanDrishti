"""
Issue clusters (spec 19).

When 500 people report the same pothole, a department needs one work item and
the public needs to see that 500 people care. A cluster provides both without
destroying anything: every original report stays its own row, keeps its own
reporter, evidence and timeline, and simply gains a foreign key to the cluster.

Nothing here deletes a citizen report. That is a hard rule.
"""

from __future__ import annotations

from django.conf import settings
from django.db import models

from jandrishti.shared.models import BaseEntity, LocatedModel


class ClusterStatus(models.TextChoices):
    ACTIVE = "ACTIVE", "Active"
    RESOLVED = "RESOLVED", "Resolved"
    DISMISSED = "DISMISSED", "Dismissed"


class IssueCluster(BaseEntity, LocatedModel):
    title = models.CharField(max_length=250)
    description = models.TextField(max_length=4000, blank=True)
    category = models.ForeignKey(
        "catalog.Category", on_delete=models.SET_NULL, null=True, related_name="clusters"
    )
    department = models.ForeignKey(
        "catalog.Department",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="clusters",
    )
    status = models.CharField(
        max_length=20, choices=ClusterStatus.choices, default=ClusterStatus.ACTIVE, db_index=True
    )

    # The report the cluster formed around. Not privileged over the others for
    # any purpose except giving the cluster a stable canonical description.
    primary_problem = models.ForeignKey(
        "problems.Problem",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="primary_for_clusters",
    )

    problem_count = models.PositiveIntegerField(default=0, db_index=True)
    total_support_count = models.PositiveIntegerField(default=0, db_index=True)
    unique_reporter_count = models.PositiveIntegerField(default=0)

    # Cluster membership is machine-proposed and human-reviewable (spec 40).
    # `review_required` is set when confidence is middling.
    review_required = models.BooleanField(default=False, db_index=True)
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "issue_cluster"
        ordering = ["-total_support_count"]
        indexes = [
            models.Index(fields=["status", "-problem_count"]),
            models.Index(fields=["category", "status"]),
            models.Index(fields=["latitude", "longitude"]),
            models.Index(fields=["department", "status"]),
        ]

    def __str__(self) -> str:
        return f"{self.title} ({self.problem_count} reports)"

    @property
    def aggregate_label(self) -> str:
        return f"Reported by {self.unique_reporter_count or self.problem_count} people"


class ClusterMembership(BaseEntity):
    """Why a problem is in a cluster, and how sure the system was.

    Keeping the evidence for the decision means a wrong merge can be audited
    and undone, rather than being an unexplained fact about the data.
    """

    class Method(models.TextChoices):
        GEOGRAPHIC = "GEOGRAPHIC", "Geographic proximity"
        TEXT_SIMILARITY = "TEXT_SIMILARITY", "Title and text similarity"
        SEMANTIC = "SEMANTIC", "Semantic similarity"
        MANUAL = "MANUAL", "Manual"

    cluster = models.ForeignKey(IssueCluster, on_delete=models.CASCADE, related_name="memberships")
    problem = models.ForeignKey(
        "problems.Problem", on_delete=models.CASCADE, related_name="cluster_memberships"
    )
    method = models.CharField(max_length=20, choices=Method.choices, default=Method.GEOGRAPHIC)
    confidence = models.FloatField(default=0.0)
    distance_metres = models.FloatField(null=True, blank=True)
    title_similarity = models.FloatField(null=True, blank=True)
    confirmed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )
    confirmed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "issue_cluster_membership"
        constraints = [
            models.UniqueConstraint(fields=["cluster", "problem"], name="uq_cluster_membership")
        ]
        indexes = [models.Index(fields=["cluster", "-confidence"])]

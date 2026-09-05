"""
Government access (spec 32).

The membership row is what makes an official an official *for a department*.
Without it, `role == GOVERNMENT_OFFICIAL` would be a nationwide licence to
close any issue in the country -- the object-level authorization hole the
security section warns about.
"""

from __future__ import annotations

from django.conf import settings
from django.db import models

from jandrishti.shared.models import BaseEntity


class DepartmentMembership(BaseEntity):
    class Role(models.TextChoices):
        OFFICER = "OFFICER", "Officer"
        SUPERVISOR = "SUPERVISOR", "Supervisor"
        HEAD = "HEAD", "Department head"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="department_memberships"
    )
    department = models.ForeignKey(
        "catalog.Department", on_delete=models.CASCADE, related_name="memberships"
    )
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.OFFICER)
    designation = models.CharField(max_length=150, blank=True)
    is_active = models.BooleanField(default=True, db_index=True)

    # Granted by an administrator, never self-assigned. Recorded here as well as
    # in the audit log so the provenance travels with the row.
    granted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )
    granted_at = models.DateTimeField(null=True, blank=True)
    revoked_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "government_department_membership"
        constraints = [
            models.UniqueConstraint(fields=["user", "department"], name="uq_department_membership")
        ]
        indexes = [models.Index(fields=["user", "is_active"])]

    def __str__(self) -> str:
        return f"{self.user} @ {self.department}"


class ProblemAssignment(BaseEntity):
    """An individual official made responsible for a specific problem."""

    problem = models.ForeignKey(
        "problems.Problem", on_delete=models.CASCADE, related_name="assignments"
    )
    assignee = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="assigned_problems",
    )
    department = models.ForeignKey(
        "catalog.Department", on_delete=models.CASCADE, related_name="assignments"
    )
    assigned_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )
    note = models.CharField(max_length=500, blank=True)
    is_current = models.BooleanField(default=True, db_index=True)

    class Meta:
        db_table = "government_problem_assignment"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["assignee", "is_current"]),
            models.Index(fields=["department", "is_current"]),
        ]
        constraints = [
            # Reassignment supersedes rather than duplicates: exactly one
            # current assignment per problem.
            models.UniqueConstraint(
                fields=["problem"],
                condition=models.Q(is_current=True),
                name="uq_one_current_assignment_per_problem",
            )
        ]

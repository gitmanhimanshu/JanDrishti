"""
The problem lifecycle: which status may follow which, and who may make the move.

This is pure domain logic. It imports no view, no serializer and no ORM query,
which is what makes the whole lifecycle unit-testable in milliseconds.
"""

from __future__ import annotations

from jandrishti.shared.domain.exceptions import PermissionDeniedError
from jandrishti.shared.domain.state_machine import StateMachine

from .enums import ProblemStatus as S

# Terminal outcomes are reachable from any open status: a report can turn out to
# be a duplicate or outside jurisdiction at any point before it closes.
_EARLY_EXITS = (
    S.REJECTED,
    S.DUPLICATE,
    S.INSUFFICIENT_EVIDENCE,
    S.OUTSIDE_JURISDICTION,
    S.ALREADY_RESOLVED,
)

TRANSITIONS: dict[str, tuple[str, ...]] = {
    S.SUBMITTED: (S.UNDER_REVIEW, S.VERIFIED, S.DEPARTMENT_ASSIGNED, *_EARLY_EXITS),
    S.UNDER_REVIEW: (S.VERIFIED, S.DEPARTMENT_ASSIGNED, *_EARLY_EXITS),
    S.VERIFIED: (S.DEPARTMENT_ASSIGNED, *_EARLY_EXITS),
    # Reassignment is a legitimate move, so DEPARTMENT_ASSIGNED can repeat via
    # the reassign use case rather than through a self-transition here.
    S.DEPARTMENT_ASSIGNED: (S.ACKNOWLEDGED, *_EARLY_EXITS),
    S.ACKNOWLEDGED: (S.INSPECTION, S.ACTION_PLANNED, *_EARLY_EXITS),
    S.INSPECTION: (S.ACTION_PLANNED, S.WORK_STARTED, *_EARLY_EXITS),
    S.ACTION_PLANNED: (S.WORK_STARTED, *_EARLY_EXITS),
    S.WORK_STARTED: (S.WORK_IN_PROGRESS, S.COMPLETED, *_EARLY_EXITS),
    S.WORK_IN_PROGRESS: (S.COMPLETED, *_EARLY_EXITS),
    S.COMPLETED: (S.VERIFICATION, S.RESOLVED, S.WORK_IN_PROGRESS),
    # Verification can send work back: if the proof does not hold up, the issue
    # returns to the department rather than quietly closing.
    S.VERIFICATION: (S.RESOLVED, S.WORK_IN_PROGRESS, S.INSUFFICIENT_EVIDENCE),
    S.RESOLVED: (),
    S.REJECTED: (S.UNDER_REVIEW,),
    S.DUPLICATE: (S.UNDER_REVIEW,),
    S.INSUFFICIENT_EVIDENCE: (S.UNDER_REVIEW,),
    S.OUTSIDE_JURISDICTION: (S.UNDER_REVIEW,),
    S.ALREADY_RESOLVED: (S.UNDER_REVIEW,),
}

problem_lifecycle: StateMachine[str] = StateMachine(
    TRANSITIONS, terminal=(S.RESOLVED,), name="problem"
)

# Who may drive which part of the lifecycle. Moderators triage; departments do
# the work; only a moderator or administrator declares something RESOLVED, so a
# department cannot close its own issue without review.
MODERATOR_STATUSES = frozenset(
    {
        S.UNDER_REVIEW,
        S.VERIFIED,
        S.DEPARTMENT_ASSIGNED,
        S.REJECTED,
        S.DUPLICATE,
        S.INSUFFICIENT_EVIDENCE,
        S.OUTSIDE_JURISDICTION,
        S.ALREADY_RESOLVED,
        S.VERIFICATION,
        S.RESOLVED,
    }
)

GOVERNMENT_STATUSES = frozenset(
    {
        S.ACKNOWLEDGED,
        S.INSPECTION,
        S.ACTION_PLANNED,
        S.WORK_STARTED,
        S.WORK_IN_PROGRESS,
        S.COMPLETED,
        S.OUTSIDE_JURISDICTION,
        S.DUPLICATE,
    }
)


def assert_actor_may_set(user, target_status: str) -> None:
    """Authorization for a status change. Server-side, role from the database."""
    if getattr(user, "is_superuser", False):
        return
    role = getattr(user, "role", None)
    if role == "ADMIN":
        return
    if role == "MODERATOR" and target_status in MODERATOR_STATUSES:
        return
    if role == "GOVERNMENT_OFFICIAL" and target_status in GOVERNMENT_STATUSES:
        return
    raise PermissionDeniedError(f"Your role is not allowed to move a problem to {target_status}.")


def is_open(status: str) -> bool:
    return status in S.open_statuses()

"""
Domain events.

Modules stay decoupled by publishing facts rather than calling each other:
`problems` publishes ProblemCreated, and `notifications`, `search`,
`issue_clustering` and `analytics` each decide for themselves whether they care.

The bus is deliberately in-process today (docs/decisions/events.md). Because
publishers only ever see this dataclass and the EventBus port, swapping the
in-process bus for Kafka later is an infrastructure change, not a domain one.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any


@dataclass(frozen=True, slots=True)
class DomainEvent:
    """Something that happened. Past tense, immutable, never a command."""

    name: str
    payload: dict[str, Any] = field(default_factory=dict)
    occurred_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    event_id: uuid.UUID = field(default_factory=uuid.uuid4)

    def to_dict(self) -> dict[str, Any]:
        return {
            "event_id": str(self.event_id),
            "name": self.name,
            "payload": self.payload,
            "occurred_at": self.occurred_at.isoformat(),
        }


# Event names. Constants rather than bare strings so a typo is an ImportError
# instead of a handler that silently never fires.
class Events:
    PROBLEM_CREATED = "problem.created"
    PROBLEM_SUPPORTED = "problem.supported"
    PROBLEM_STATUS_CHANGED = "problem.status_changed"
    PROBLEM_EVIDENCE_ADDED = "problem.evidence_added"
    PROBLEM_CLUSTERED = "problem.clustered"

    EXPERIENCE_CREATED = "experience.created"
    EXPERIENCE_SUPPORTED = "experience.supported"

    COMMENT_CREATED = "comment.created"

    GOVERNMENT_RESPONSE_ADDED = "government.response_added"

    VERIFICATION_SUBMITTED = "verification.submitted"
    VERIFICATION_COMPLETED = "verification.completed"

    EVIDENCE_VERIFIED = "evidence.verified"

    PROJECT_CREATED = "project.created"
    PROJECT_UPDATED = "project.updated"
    PROJECT_MILESTONE_COMPLETED = "project.milestone_completed"

    CONTRIBUTION_RECORDED = "funding.contribution_recorded"
    EXPENSE_RECORDED = "funding.expense_recorded"

    CONTENT_REPORTED = "moderation.content_reported"


def make_event(name: str, **payload: Any) -> DomainEvent:
    return DomainEvent(name=name, payload=payload)

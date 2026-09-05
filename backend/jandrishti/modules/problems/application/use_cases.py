"""
Problem use cases.

Each class is one intent. Views construct a command and call `execute`; the
transaction, the event publication and the audit trail are handled here so that
no rule is duplicated between the citizen API and the government dashboard.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

from django.db import IntegrityError, transaction
from django.db.models import F
from django.utils import timezone

from jandrishti.modules.audit.application.recorder import record_audit
from jandrishti.modules.catalog.application.routing import routing_service
from jandrishti.modules.catalog.models import Category, Department
from jandrishti.modules.media.application.service import MediaService
from jandrishti.modules.media.models import MediaAttachment
from jandrishti.shared.application.use_case import Actor, UseCase
from jandrishti.shared.domain.events import Events, make_event
from jandrishti.shared.domain.exceptions import (
    ConflictError,
    NotFoundError,
    PermissionDeniedError,
    ValidationError,
)
from jandrishti.shared.domain.value_objects import GeoPoint, Location

from ..domain.enums import ProblemPriority, ProblemStatus
from ..domain.lifecycle import assert_actor_may_set, problem_lifecycle
from ..domain.ranking import compute_trend_score
from ..models import GovernmentResponse, Problem, ProblemSupport, ProblemTimelineEvent

logger = logging.getLogger(__name__)


def refresh_trend_score(problem: Problem) -> None:
    """Recompute and store the momentum score after engagement changes."""
    Problem.objects.filter(pk=problem.pk).update(
        trend_score=compute_trend_score(
            support_count=problem.support_count,
            report_count=problem.report_count,
            comment_count=problem.comment_count,
            last_activity_at=problem.last_activity_at,
        )
    )


# ---------------------------------------------------------------------------
# Create
# ---------------------------------------------------------------------------
@dataclass(slots=True)
class CreateProblemCommand:
    title: str
    description: str
    category_id: str | None = None
    department_id: str | None = None
    priority: str = ProblemPriority.MEDIUM
    address: str = ""
    city: str = ""
    district: str = ""
    state: str = ""
    pincode: str = ""
    latitude: float | None = None
    longitude: float | None = None
    media_ids: list[str] = field(default_factory=list)
    is_anonymous_report: bool = False
    actor: Actor = field(default_factory=Actor.anonymous)


class CreateProblemUseCase(UseCase[CreateProblemCommand, Problem]):
    """Report a problem.

    Routing to a department is attempted immediately, because an unrouted
    report helps nobody -- but a failure to route is not a failure to submit.
    The report stands and a human assigns it later.
    """

    def handle(self, request: CreateProblemCommand) -> Problem:
        user = request.actor.require_authenticated()
        if not user.can_interact:
            raise PermissionDeniedError("This account cannot post at the moment.")

        title = request.title.strip()
        description = request.description.strip()
        if len(title) < 10:
            raise ValidationError("Give the problem a title of at least 10 characters.")
        if len(description) < 30:
            raise ValidationError(
                "Describe the problem in at least 30 characters so it can be acted on."
            )

        # Validating through the value object means an impossible coordinate is
        # rejected by the domain, not by a database constraint at write time.
        point = GeoPoint.parse(request.latitude, request.longitude)
        location = Location(
            address=request.address.strip(),
            city=request.city.strip(),
            district=request.district.strip(),
            state=request.state.strip(),
            pincode=request.pincode.strip(),
            point=point,
        )

        category = self._resolve_category(request.category_id)
        department = self._resolve_department(request.department_id)
        routing_reason = ""
        if department is None and category is not None:
            decision = routing_service.route(
                category=category,
                state=location.state,
                district=location.district,
                city=location.city,
            )
            department = decision.department
            routing_reason = decision.reason

        problem = Problem.objects.create(
            title=title,
            description=description,
            reporter=user,
            category=category,
            department=department,
            priority=request.priority
            if request.priority in ProblemPriority.values
            else ProblemPriority.MEDIUM,
            address=location.address,
            city=location.city,
            district=location.district,
            state=location.state,
            pincode=location.pincode,
            latitude=point.latitude if point else None,
            longitude=point.longitude if point else None,
            is_anonymous_report=request.is_anonymous_report,
            status=(ProblemStatus.DEPARTMENT_ASSIGNED if department else ProblemStatus.SUBMITTED),
            last_status_change_at=timezone.now(),
        )

        attached = 0
        if request.media_ids:
            attached = MediaService().attach(
                request.media_ids,
                target_type=MediaAttachment.Target.PROBLEM,
                target_id=problem.id,
                owner=user,
            )
            if attached:
                Problem.objects.filter(pk=problem.pk).update(evidence_count=attached)
                problem.evidence_count = attached

        ProblemTimelineEvent.objects.create(
            problem=problem,
            kind=ProblemTimelineEvent.Kind.REPORTED,
            title="Problem reported",
            description=(
                "Reported by a citizen." if request.is_anonymous_report else f"Reported by {user}."
            ),
            to_status=problem.status,
            actor=user,
            actor_label="Citizen" if request.is_anonymous_report else str(user),
        )
        if department:
            ProblemTimelineEvent.objects.create(
                problem=problem,
                kind=ProblemTimelineEvent.Kind.DEPARTMENT_ASSIGNED,
                title=f"Assigned to {department.name}",
                description=routing_reason,
                to_status=ProblemStatus.DEPARTMENT_ASSIGNED,
                actor_label="Automatic routing",
            )

        refresh_trend_score(problem)

        # Duplicate detection, notifications and search indexing all hang off
        # this event. None of them belongs on the request path.
        self.record(
            make_event(
                Events.PROBLEM_CREATED,
                problem_id=str(problem.public_id),
                problem_pk=problem.id,
                category_id=category.id if category else None,
                department_id=department.id if department else None,
                reporter_id=str(user.id),
            )
        )
        record_audit(
            action="problem.created",
            actor=user,
            target=f"problem:{problem.public_id}",
            metadata={"department": department.name if department else None, "media": attached},
            ip_address=request.actor.ip_address or None,
            request_id=request.actor.request_id,
        )
        return problem

    @staticmethod
    def _resolve_category(category_id: str | None) -> Category | None:
        if not category_id:
            return None
        category = Category.objects.filter(public_id=category_id, is_active=True).first()
        if category is None:
            raise ValidationError("That category does not exist.")
        return category

    @staticmethod
    def _resolve_department(department_id: str | None) -> Department | None:
        if not department_id:
            return None
        return Department.objects.filter(public_id=department_id, is_active=True).first()


# ---------------------------------------------------------------------------
# Support
# ---------------------------------------------------------------------------
@dataclass(slots=True)
class SupportProblemCommand:
    problem_id: str
    note: str = ""
    actor: Actor = field(default_factory=Actor.anonymous)


@dataclass(slots=True)
class SupportResult:
    problem: Problem
    support_count: int
    already_supported: bool


class SupportProblemUseCase(UseCase[SupportProblemCommand, SupportResult]):
    """`I face this problem too`.

    Concurrency-safe by construction: the unique constraint decides whether the
    support is new, and the cached counter moves with an atomic F-expression in
    the same transaction. A thousand simultaneous supporters produce exactly a
    thousand rows and a counter that agrees with them.
    """

    def handle(self, request: SupportProblemCommand) -> SupportResult:
        user = request.actor.require_authenticated()
        if not user.can_interact:
            raise PermissionDeniedError("This account cannot interact at the moment.")

        problem = Problem.objects.public().filter(public_id=request.problem_id).first()
        if problem is None:
            raise NotFoundError("Problem not found.")

        try:
            with transaction.atomic():
                ProblemSupport.objects.create(
                    problem=problem, user=user, note=request.note.strip()[:300]
                )
                Problem.objects.filter(pk=problem.pk).update(
                    support_count=F("support_count") + 1, last_activity_at=timezone.now()
                )
        except IntegrityError:
            # The unique constraint fired: this user already supports it. That
            # is not an error worth showing -- return the current state.
            problem.refresh_from_db(fields=["support_count"])
            return SupportResult(problem, problem.support_count, already_supported=True)

        problem.refresh_from_db(fields=["support_count", "last_activity_at"])
        refresh_trend_score(problem)

        self.record(
            make_event(
                Events.PROBLEM_SUPPORTED,
                problem_id=str(problem.public_id),
                problem_pk=problem.id,
                user_id=str(user.id),
                support_count=problem.support_count,
            )
        )
        return SupportResult(problem, problem.support_count, already_supported=False)


@dataclass(slots=True)
class WithdrawSupportCommand:
    problem_id: str
    actor: Actor = field(default_factory=Actor.anonymous)


class WithdrawSupportUseCase(UseCase[WithdrawSupportCommand, SupportResult]):
    """Withdrawing is allowed -- a person may no longer be affected."""

    def handle(self, request: WithdrawSupportCommand) -> SupportResult:
        user = request.actor.require_authenticated()
        problem = Problem.objects.public().filter(public_id=request.problem_id).first()
        if problem is None:
            raise NotFoundError("Problem not found.")

        deleted, _ = ProblemSupport.objects.filter(problem=problem, user=user).delete()
        if deleted:
            # `Greatest` guards the floor: the column is unsigned, and a stale
            # cache must never try to go below zero.
            from django.db.models.functions import Greatest

            Problem.objects.filter(pk=problem.pk).update(
                support_count=Greatest(F("support_count") - 1, 0)
            )
        problem.refresh_from_db(fields=["support_count"])
        refresh_trend_score(problem)
        return SupportResult(problem, problem.support_count, already_supported=False)


# ---------------------------------------------------------------------------
# Status
# ---------------------------------------------------------------------------
@dataclass(slots=True)
class UpdateProblemStatusCommand:
    problem_id: str
    to_status: str
    note: str = ""
    actor: Actor = field(default_factory=Actor.anonymous)


class UpdateProblemStatusUseCase(UseCase[UpdateProblemStatusCommand, Problem]):
    """Move a problem along its lifecycle.

    Two independent checks, both server-side: the transition must be legal for
    the current status, and the actor's role must be permitted to make it.
    """

    def handle(self, request: UpdateProblemStatusCommand) -> Problem:
        user = request.actor.require_authenticated()

        if request.to_status not in ProblemStatus.values:
            raise ValidationError("Unknown status.")

        problem = (
            Problem.objects.select_for_update()
            .select_related("department")
            .filter(public_id=request.problem_id)
            .first()
        )
        if problem is None:
            raise NotFoundError("Problem not found.")

        assert_actor_may_set(user, request.to_status)
        self._assert_department_scope(user, problem)
        problem_lifecycle.assert_can(problem.status, request.to_status)

        previous = problem.status
        now = timezone.now()
        problem.status = request.to_status
        problem.last_status_change_at = now
        problem.last_activity_at = now
        if request.to_status == ProblemStatus.ACKNOWLEDGED and not problem.acknowledged_at:
            problem.acknowledged_at = now
        if request.to_status == ProblemStatus.RESOLVED:
            problem.resolved_at = now
        if request.to_status in ProblemStatus.closed_statuses() and request.note:
            problem.closure_reason = request.note[:500]
        problem.save(
            update_fields=[
                "status",
                "last_status_change_at",
                "last_activity_at",
                "acknowledged_at",
                "resolved_at",
                "closure_reason",
                "updated_at",
            ]
        )

        ProblemTimelineEvent.objects.create(
            problem=problem,
            kind=(
                ProblemTimelineEvent.Kind.RESOLVED
                if request.to_status == ProblemStatus.RESOLVED
                else ProblemTimelineEvent.Kind.STATUS_CHANGED
            ),
            title=f"Status changed to {ProblemStatus(request.to_status).label}",
            description=request.note[:3000],
            from_status=previous,
            to_status=request.to_status,
            actor=user,
            actor_label=(
                problem.department.name if problem.department and user.is_government else str(user)
            ),
        )

        self.record(
            make_event(
                Events.PROBLEM_STATUS_CHANGED,
                problem_id=str(problem.public_id),
                problem_pk=problem.id,
                from_status=previous,
                to_status=request.to_status,
                actor_id=str(user.id),
            )
        )
        record_audit(
            action="problem.status_changed",
            actor=user,
            target=f"problem:{problem.public_id}",
            metadata={"from": previous, "to": request.to_status, "note": request.note[:200]},
            ip_address=request.actor.ip_address or None,
            request_id=request.actor.request_id,
        )
        return problem

    @staticmethod
    def _assert_department_scope(user: Any, problem: Problem) -> None:
        """A government official acts only within their own department subtree.

        Without this, any official could close any issue in the country -- the
        classic broken-object-level-authorization hole.
        """
        if getattr(user, "is_superuser", False) or user.role in {"ADMIN", "MODERATOR"}:
            return
        if user.role != "GOVERNMENT_OFFICIAL":
            raise PermissionDeniedError("Only officials can update problem status.")

        from jandrishti.modules.government.models import DepartmentMembership

        if problem.department_id is None:
            raise ConflictError("This problem has not been assigned to a department yet.")
        allowed = DepartmentMembership.objects.filter(user=user, is_active=True).values_list(
            "department__path", flat=True
        )
        department_path = problem.department.path
        if not any(
            department_path == path or department_path.startswith(f"{path}/") for path in allowed
        ):
            raise PermissionDeniedError("This problem belongs to another department.")


# ---------------------------------------------------------------------------
# Government response
# ---------------------------------------------------------------------------
@dataclass(slots=True)
class AddGovernmentResponseCommand:
    problem_id: str
    message: str
    kind: str = GovernmentResponse.Kind.PROGRESS_UPDATE
    expected_resolution_date: Any = None
    reference_number: str = ""
    media_ids: list[str] = field(default_factory=list)
    actor: Actor = field(default_factory=Actor.anonymous)


class AddGovernmentResponseUseCase(UseCase[AddGovernmentResponseCommand, GovernmentResponse]):
    def handle(self, request: AddGovernmentResponseCommand) -> GovernmentResponse:
        user = request.actor.require_role("GOVERNMENT_OFFICIAL", "ADMIN")
        message = request.message.strip()
        if len(message) < 10:
            raise ValidationError("A response needs at least 10 characters.")

        problem = (
            Problem.objects.select_related("department")
            .filter(public_id=request.problem_id)
            .first()
        )
        if problem is None:
            raise NotFoundError("Problem not found.")
        UpdateProblemStatusUseCase._assert_department_scope(user, problem)

        response = GovernmentResponse.objects.create(
            problem=problem,
            department=problem.department,
            official=user,
            kind=request.kind
            if request.kind in GovernmentResponse.Kind.values
            else GovernmentResponse.Kind.PROGRESS_UPDATE,
            message=message,
            expected_resolution_date=request.expected_resolution_date,
            reference_number=request.reference_number[:80],
        )
        if request.media_ids:
            MediaService().attach(
                request.media_ids,
                target_type=MediaAttachment.Target.GOVERNMENT_RESPONSE,
                target_id=response.id,
                owner=user,
            )

        Problem.objects.filter(pk=problem.pk).update(last_activity_at=timezone.now())
        ProblemTimelineEvent.objects.create(
            problem=problem,
            kind=ProblemTimelineEvent.Kind.GOVERNMENT_RESPONSE,
            title=response.get_kind_display(),
            description=message[:3000],
            actor=user,
            actor_label=problem.department.name if problem.department else "Government",
        )

        self.record(
            make_event(
                Events.GOVERNMENT_RESPONSE_ADDED,
                problem_id=str(problem.public_id),
                problem_pk=problem.id,
                response_id=str(response.public_id),
            )
        )
        record_audit(
            action="problem.government_response_added",
            actor=user,
            target=f"problem:{problem.public_id}",
            metadata={"kind": response.kind},
            ip_address=request.actor.ip_address or None,
        )
        return response


# ---------------------------------------------------------------------------
# Evidence
# ---------------------------------------------------------------------------
@dataclass(slots=True)
class AddEvidenceCommand:
    problem_id: str
    media_ids: list[str]
    actor: Actor = field(default_factory=Actor.anonymous)


class AddEvidenceUseCase(UseCase[AddEvidenceCommand, int]):
    """Anyone signed in can add evidence -- corroboration is the point.

    What they cannot do is mark it verified. That is a separate, human decision
    (spec 17), and nothing on this path can set VERIFIED.
    """

    def handle(self, request: AddEvidenceCommand) -> int:
        user = request.actor.require_authenticated()
        problem = Problem.objects.public().filter(public_id=request.problem_id).first()
        if problem is None:
            raise NotFoundError("Problem not found.")
        if not request.media_ids:
            raise ValidationError("No evidence was attached.")

        attached = MediaService().attach(
            request.media_ids,
            target_type=MediaAttachment.Target.PROBLEM,
            target_id=problem.id,
            owner=user,
        )
        Problem.objects.filter(pk=problem.pk).update(
            evidence_count=F("evidence_count") + attached, last_activity_at=timezone.now()
        )
        ProblemTimelineEvent.objects.create(
            problem=problem,
            kind=ProblemTimelineEvent.Kind.EVIDENCE_ADDED,
            title=f"{attached} file(s) of evidence added",
            actor=user,
            actor_label=str(user),
        )
        self.record(
            make_event(
                Events.PROBLEM_EVIDENCE_ADDED,
                problem_id=str(problem.public_id),
                problem_pk=problem.id,
                count=attached,
            )
        )
        return attached

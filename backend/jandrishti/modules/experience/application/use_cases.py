"""Experience use cases: publish, support, link to problems."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from django.db import IntegrityError, transaction
from django.db.models import F
from django.db.models.functions import Greatest
from django.utils import timezone

from jandrishti.modules.catalog.models import Category, Department
from jandrishti.modules.media.application.service import MediaService
from jandrishti.modules.media.models import MediaAttachment
from jandrishti.modules.problems.models import Problem
from jandrishti.shared.application.use_case import Actor, UseCase
from jandrishti.shared.domain.events import Events, make_event
from jandrishti.shared.domain.exceptions import (
    NotFoundError,
    PermissionDeniedError,
    ValidationError,
)

from ..domain.credibility import CredibilityInputs, compute_credibility
from ..models import (
    Experience,
    ExperienceStatus,
    ExperienceSupport,
    ExperienceType,
    ProblemExperienceLink,
)


def recompute_credibility(experience: Experience) -> float:
    """Rebuild the credibility score from current facts."""
    author = experience.author
    profile = getattr(author, "professional_profile", None) if author else None
    domain_matches = bool(
        profile
        and experience.category
        and profile.domain.lower() in experience.category.path.lower()
    )
    score = compute_credibility(
        CredibilityInputs(
            author_verified=bool(author and author.is_professionally_verified),
            author_category=getattr(author, "verified_category", "") or "",
            domain_matches_category=domain_matches,
            years_of_experience=getattr(profile, "years_of_experience", 0) or 0,
            evidence_count=experience.evidence_count,
            linked_problem_count=experience.problem_links.count(),
            support_count=experience.support_count,
            comment_count=experience.comment_count,
            has_root_cause=bool(experience.root_cause.strip()),
            has_implementation=bool(experience.implementation.strip()),
            has_expected_impact=bool(experience.expected_impact.strip()),
            has_cost_estimate=bool(experience.cost_implications.strip()),
        )
    )
    Experience.objects.filter(pk=experience.pk).update(credibility_score=score)
    # Keep the in-memory instance in step: `.update()` writes the row without
    # touching the object the caller is about to serialise.
    experience.credibility_score = score
    return score


@dataclass(slots=True)
class CreateExperienceCommand:
    title: str
    personal_experience: str
    recommendation: str
    experience_type: str = ExperienceType.PROFESSIONAL_EXPERIENCE
    observed_problem: str = ""
    context: str = ""
    root_cause: str = ""
    implementation: str = ""
    expected_impact: str = ""
    challenges: str = ""
    cost_implications: str = ""
    category_id: str | None = None
    department_id: str | None = None
    state: str = ""
    district: str = ""
    city: str = ""
    media_ids: list[str] = field(default_factory=list)
    related_problem_ids: list[str] = field(default_factory=list)
    actor: Actor = field(default_factory=Actor.anonymous)


class CreateExperienceUseCase(UseCase[CreateExperienceCommand, Experience]):
    """Publish an experience or idea.

    Open to any signed-in account, by design. The platform values relevant
    experience over employment status (spec 3B), so eligibility is not gated on
    verification -- verification affects how the contribution is *presented* and
    scored, not whether it may exist.
    """

    def handle(self, request: CreateExperienceCommand) -> Experience:
        user = request.actor.require_authenticated()
        if not user.can_interact:
            raise PermissionDeniedError("This account cannot post at the moment.")

        title = request.title.strip()
        if len(title) < 10:
            raise ValidationError("Give the contribution a title of at least 10 characters.")
        if len(request.personal_experience.strip()) < 50:
            raise ValidationError(
                "Describe your experience in at least 50 characters so others can judge it."
            )
        if len(request.recommendation.strip()) < 30:
            raise ValidationError("A recommendation of at least 30 characters is needed.")

        category = (
            Category.objects.filter(public_id=request.category_id, is_active=True).first()
            if request.category_id
            else None
        )
        department = (
            Department.objects.filter(public_id=request.department_id, is_active=True).first()
            if request.department_id
            else None
        )

        experience = Experience.objects.create(
            title=title,
            experience_type=(
                request.experience_type
                if request.experience_type in ExperienceType.values
                else ExperienceType.OTHER
            ),
            status=ExperienceStatus.PUBLISHED,
            author=user,
            observed_problem=request.observed_problem.strip(),
            context=request.context.strip(),
            root_cause=request.root_cause.strip(),
            personal_experience=request.personal_experience.strip(),
            recommendation=request.recommendation.strip(),
            implementation=request.implementation.strip(),
            expected_impact=request.expected_impact.strip(),
            challenges=request.challenges.strip(),
            cost_implications=request.cost_implications.strip(),
            category=category,
            department=department,
            state=request.state.strip(),
            district=request.district.strip(),
            city=request.city.strip(),
            author_was_verified=user.is_professionally_verified,
            author_category_at_post=user.verified_category or "",
        )

        if request.media_ids:
            attached = MediaService().attach(
                request.media_ids,
                target_type=MediaAttachment.Target.EXPERIENCE,
                target_id=experience.id,
                owner=user,
            )
            Experience.objects.filter(pk=experience.pk).update(evidence_count=attached)
            experience.evidence_count = attached

        self._link_problems(experience, request.related_problem_ids, user)
        recompute_credibility(experience)

        self.record(
            make_event(
                Events.EXPERIENCE_CREATED,
                experience_id=str(experience.public_id),
                experience_pk=experience.id,
                author_id=str(user.id),
            )
        )
        return experience

    @staticmethod
    def _link_problems(experience: Experience, problem_ids: list[str], user: Any) -> None:
        if not problem_ids:
            return
        problems = Problem.objects.public().filter(public_id__in=problem_ids[:20])
        ProblemExperienceLink.objects.bulk_create(
            [
                ProblemExperienceLink(
                    problem=problem, experience=experience, linked_by=user, is_author_link=True
                )
                for problem in problems
            ],
            ignore_conflicts=True,
        )


@dataclass(slots=True)
class SupportExperienceCommand:
    experience_id: str
    actor: Actor = field(default_factory=Actor.anonymous)


@dataclass(slots=True)
class ExperienceSupportResult:
    support_count: int
    already_supported: bool


class SupportExperienceUseCase(UseCase[SupportExperienceCommand, ExperienceSupportResult]):
    """Same concurrency discipline as problem support: constraint first, counter second."""

    def handle(self, request: SupportExperienceCommand) -> ExperienceSupportResult:
        user = request.actor.require_authenticated()
        if not user.can_interact:
            raise PermissionDeniedError("This account cannot interact at the moment.")

        experience = Experience.objects.public().filter(public_id=request.experience_id).first()
        if experience is None:
            raise NotFoundError("Experience not found.")

        try:
            with transaction.atomic():
                ExperienceSupport.objects.create(experience=experience, user=user)
                Experience.objects.filter(pk=experience.pk).update(
                    support_count=F("support_count") + 1, last_activity_at=timezone.now()
                )
        except IntegrityError:
            experience.refresh_from_db(fields=["support_count"])
            return ExperienceSupportResult(experience.support_count, already_supported=True)

        experience.refresh_from_db(fields=["support_count"])
        recompute_credibility(experience)
        self.record(
            make_event(
                Events.EXPERIENCE_SUPPORTED,
                experience_id=str(experience.public_id),
                experience_pk=experience.id,
                user_id=str(user.id),
            )
        )
        return ExperienceSupportResult(experience.support_count, already_supported=False)


@dataclass(slots=True)
class WithdrawExperienceSupportCommand:
    experience_id: str
    actor: Actor = field(default_factory=Actor.anonymous)


class WithdrawExperienceSupportUseCase(
    UseCase[WithdrawExperienceSupportCommand, ExperienceSupportResult]
):
    def handle(self, request: WithdrawExperienceSupportCommand) -> ExperienceSupportResult:
        user = request.actor.require_authenticated()
        experience = Experience.objects.public().filter(public_id=request.experience_id).first()
        if experience is None:
            raise NotFoundError("Experience not found.")

        deleted, _ = ExperienceSupport.objects.filter(experience=experience, user=user).delete()
        if deleted:
            Experience.objects.filter(pk=experience.pk).update(
                support_count=Greatest(F("support_count") - 1, 0)
            )
        experience.refresh_from_db(fields=["support_count"])
        recompute_credibility(experience)
        return ExperienceSupportResult(experience.support_count, already_supported=False)


@dataclass(slots=True)
class LinkExperienceToProblemCommand:
    experience_id: str
    problem_id: str
    relevance_note: str = ""
    actor: Actor = field(default_factory=Actor.anonymous)


class LinkExperienceToProblemUseCase(
    UseCase[LinkExperienceToProblemCommand, ProblemExperienceLink]
):
    """Anyone signed in may propose a link -- connecting knowledge to problems
    is the whole point, and a wrong link is a moderation matter, not a
    permissions one."""

    def handle(self, request: LinkExperienceToProblemCommand) -> ProblemExperienceLink:
        user = request.actor.require_authenticated()
        experience = Experience.objects.public().filter(public_id=request.experience_id).first()
        problem = Problem.objects.public().filter(public_id=request.problem_id).first()
        if experience is None or problem is None:
            raise NotFoundError("Experience or problem not found.")

        link, _created = ProblemExperienceLink.objects.get_or_create(
            problem=problem,
            experience=experience,
            defaults={
                "linked_by": user,
                "is_author_link": experience.author_id == user.id,
                "relevance_note": request.relevance_note[:300],
            },
        )
        recompute_credibility(experience)
        return link

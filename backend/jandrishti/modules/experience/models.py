"""
Experience & Ideas (spec 20-24).

The second first-class section. Where a Problem says "this is wrong", an
Experience says "here is what I have seen and what I would do about it". The
structured fields exist because unstructured advice is hard for a department to
act on: root cause, recommendation, implementation, expected impact and cost
are separate columns so they can be read separately.
"""

from __future__ import annotations

from django.conf import settings
from django.db import models
from django.utils import timezone

from jandrishti.shared.models import BaseEntity, SoftDeleteModel


class ExperienceType(models.TextChoices):
    PROFESSIONAL_EXPERIENCE = "PROFESSIONAL_EXPERIENCE", "Professional experience"
    ROOT_CAUSE_ANALYSIS = "ROOT_CAUSE_ANALYSIS", "Root cause analysis"
    POLICY_IDEA = "POLICY_IDEA", "Policy idea"
    RECOMMENDATION = "RECOMMENDATION", "Recommendation"
    BEST_PRACTICE = "BEST_PRACTICE", "Best practice"
    GOVERNANCE_IMPROVEMENT = "GOVERNANCE_IMPROVEMENT", "Governance improvement"
    COST_REDUCTION = "COST_REDUCTION", "Cost reduction"
    PROCESS_IMPROVEMENT = "PROCESS_IMPROVEMENT", "Process improvement"
    TECHNOLOGY_IMPROVEMENT = "TECHNOLOGY_IMPROVEMENT", "Technology improvement"
    OTHER = "OTHER", "Other"


class ExperienceStatus(models.TextChoices):
    PUBLISHED = "PUBLISHED", "Published"
    DRAFT = "DRAFT", "Draft"
    UNDER_MODERATION = "UNDER_MODERATION", "Under moderation"
    REMOVED = "REMOVED", "Removed"


class ExperienceQuerySet(models.QuerySet):
    def public(self) -> ExperienceQuerySet:
        return self.filter(deleted_at__isnull=True, status=ExperienceStatus.PUBLISHED)

    def with_display_relations(self) -> ExperienceQuerySet:
        return self.select_related(
            "author", "author__professional_profile", "category", "department"
        )


class ExperienceManager(models.Manager.from_queryset(ExperienceQuerySet)):  # type: ignore[misc]
    def get_queryset(self) -> ExperienceQuerySet:
        return super().get_queryset().filter(deleted_at__isnull=True)


class Experience(BaseEntity, SoftDeleteModel):
    title = models.CharField(max_length=200)
    slug = models.SlugField(max_length=220, blank=True)
    experience_type = models.CharField(
        max_length=40,
        choices=ExperienceType.choices,
        default=ExperienceType.PROFESSIONAL_EXPERIENCE,
        db_index=True,
    )
    status = models.CharField(
        max_length=20,
        choices=ExperienceStatus.choices,
        default=ExperienceStatus.PUBLISHED,
        db_index=True,
    )

    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="experiences",
    )

    # The structured body from spec 22.
    observed_problem = models.TextField(max_length=4000, blank=True)
    context = models.TextField(max_length=4000, blank=True)
    root_cause = models.TextField(max_length=4000, blank=True)
    personal_experience = models.TextField(max_length=6000)
    recommendation = models.TextField(max_length=6000)
    implementation = models.TextField(max_length=4000, blank=True)
    expected_impact = models.TextField(max_length=4000, blank=True)
    challenges = models.TextField(max_length=4000, blank=True)
    cost_implications = models.TextField(max_length=2000, blank=True)

    category = models.ForeignKey(
        "catalog.Category",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="experiences",
    )
    department = models.ForeignKey(
        "catalog.Department",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="experiences",
    )
    state = models.CharField(max_length=120, blank=True, db_index=True)
    district = models.CharField(max_length=120, blank=True)
    city = models.CharField(max_length=120, blank=True)

    support_count = models.PositiveIntegerField(default=0, db_index=True)
    comment_count = models.PositiveIntegerField(default=0)
    view_count = models.PositiveBigIntegerField(default=0)
    evidence_count = models.PositiveIntegerField(default=0)

    # Credibility is a blend, not a like count (spec 31). Recomputed by a
    # background job; support is one input among several and never the only one.
    credibility_score = models.FloatField(default=0.0, db_index=True)
    last_activity_at = models.DateTimeField(default=timezone.now, db_index=True)

    # Snapshot of the author's verification at publication time. Without it, a
    # later change to the author's status would silently rewrite the apparent
    # provenance of an old post.
    author_was_verified = models.BooleanField(default=False)
    author_category_at_post = models.CharField(max_length=40, blank=True)

    objects = ExperienceManager()
    all_objects = models.Manager.from_queryset(ExperienceQuerySet)()

    class Meta:
        db_table = "experience"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["status", "-created_at"]),
            models.Index(fields=["status", "-credibility_score"]),
            models.Index(fields=["experience_type", "status"]),
            models.Index(fields=["category", "status"]),
            models.Index(fields=["author", "-created_at"]),
        ]

    def __str__(self) -> str:
        return self.title

    def save(self, *args, **kwargs):
        if not self.slug:
            from django.utils.text import slugify

            self.slug = slugify(self.title)[:220]
        super().save(*args, **kwargs)


class ExperienceSupport(models.Model):
    """`I support this idea`. One per person, enforced by the database.

    Support signals agreement, not correctness -- the UI says so, and nothing
    in ranking treats it as proof (spec 24, 31).
    """

    experience = models.ForeignKey(Experience, on_delete=models.CASCADE, related_name="supports")
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="experience_supports"
    )
    created_at = models.DateTimeField(default=timezone.now, db_index=True)

    class Meta:
        db_table = "experience_supports"
        constraints = [
            models.UniqueConstraint(fields=["experience", "user"], name="uq_experience_support")
        ]
        indexes = [models.Index(fields=["user", "-created_at"])]

    def __str__(self) -> str:
        return f"{self.user_id} supports experience {self.experience_id}"


class ProblemExperienceLink(BaseEntity):
    """Many-to-many between problems and experiences, with provenance.

    An experience can address several problems and a problem can attract several
    experiences (spec 22). `linked_by` and `is_author_link` record whether the
    connection was drawn by the author or suggested and later confirmed.
    """

    problem = models.ForeignKey(
        "problems.Problem", on_delete=models.CASCADE, related_name="experience_links"
    )
    experience = models.ForeignKey(
        Experience, on_delete=models.CASCADE, related_name="problem_links"
    )
    linked_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="+"
    )
    is_author_link = models.BooleanField(default=True)
    relevance_note = models.CharField(max_length=300, blank=True)

    class Meta:
        db_table = "problem_experience_link"
        constraints = [
            models.UniqueConstraint(
                fields=["problem", "experience"], name="uq_problem_experience_link"
            )
        ]
        indexes = [
            models.Index(fields=["problem", "-created_at"]),
            models.Index(fields=["experience", "-created_at"]),
        ]

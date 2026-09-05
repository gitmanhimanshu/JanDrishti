"""
Clustering service.

Runs off the ProblemCreated event via Celery, never on the request path: a
citizen submitting a report should not wait on a similarity search.

The candidate query is bounded by a bounding box, a category and a time window
before any scoring happens, so this stays cheap no matter how large the archive
gets.
"""

from __future__ import annotations

import logging
from datetime import timedelta

from django.conf import settings
from django.db import transaction
from django.db.models import Count, Q, Sum
from django.utils import timezone

from jandrishti.modules.problems.models import Problem, ProblemTimelineEvent
from jandrishti.shared.domain.value_objects import GeoPoint
from jandrishti.shared.infrastructure.cache import distributed_lock

from ..domain.detection import Candidate, best_match, score_candidate
from ..models import ClusterMembership, IssueCluster

logger = logging.getLogger(__name__)

MAX_CANDIDATES = 200


class IssueClusteringService:
    def __init__(self) -> None:
        self._radius_m = float(settings.CLUSTERING_RADIUS_METRES)
        self._window_days = int(settings.CLUSTERING_WINDOW_DAYS)

    # -- candidate selection -------------------------------------------------

    def _candidates(self, problem: Problem) -> list[Candidate]:
        cutoff = timezone.now() - timedelta(days=self._window_days)
        queryset = (
            Problem.objects.public()
            .exclude(pk=problem.pk)
            .filter(created_at__gte=cutoff)
            .only(
                "id",
                "title",
                "description",
                "category_id",
                "latitude",
                "longitude",
                "created_at",
                "cluster_id",
            )
        )

        if problem.has_coordinates:
            point = GeoPoint(problem.latitude, problem.longitude)
            # Search a wider box than the merge radius so a near-miss is still
            # scored (and can be proposed for review) rather than never seen.
            min_lat, max_lat, min_lng, max_lng = point.bounding_box((self._radius_m * 3) / 1000.0)
            queryset = queryset.filter(
                latitude__gte=min_lat,
                latitude__lte=max_lat,
                longitude__gte=min_lng,
                longitude__lte=max_lng,
            )
        else:
            # No GPS: fall back to administrative area, which is coarse but is
            # the only locality signal available.
            queryset = queryset.filter(
                Q(city__iexact=problem.city) | Q(district__iexact=problem.district)
            ).exclude(city="", district="")

        if problem.category_id:
            queryset = queryset.filter(category_id=problem.category_id)

        return [
            Candidate(
                problem_id=row.id,
                title=row.title,
                description=row.description,
                category_id=row.category_id,
                latitude=row.latitude,
                longitude=row.longitude,
                created_at=row.created_at,
                cluster_id=row.cluster_id,
            )
            for row in queryset.order_by("-created_at")[:MAX_CANDIDATES]
        ]

    # -- main entry point ----------------------------------------------------

    def process(self, problem_pk: int) -> IssueCluster | None:
        """Find or create the cluster this problem belongs to.

        Idempotent: a problem already in a cluster is left alone, so a retried
        Celery task cannot double-count.
        """
        problem = Problem.objects.filter(pk=problem_pk).select_related("category").first()
        if problem is None or problem.cluster_id:
            return None

        candidates = self._candidates(problem)
        if not candidates:
            return None

        point = GeoPoint(problem.latitude, problem.longitude) if problem.has_coordinates else None
        scores = [
            score_candidate(
                new_title=problem.title,
                new_description=problem.description,
                new_category_id=problem.category_id,
                new_point=point,
                new_created_at=problem.created_at,
                candidate=candidate,
                radius_metres=self._radius_m,
                window_days=self._window_days,
            )
            for candidate in candidates
        ]
        match = best_match(scores)
        if match is None or match.score < 0.62:
            return None

        # Two workers scoring near-identical reports at the same instant would
        # otherwise create two clusters for one pothole. This is one of the few
        # genuinely distributed races on the platform, so it gets a real lock
        # (spec 49) -- everything else relies on database constraints.
        lock_key = f"cluster:{problem.category_id}:{round(problem.latitude or 0, 3)}:{round(problem.longitude or 0, 3)}"
        with distributed_lock(lock_key, timeout=30) as acquired:
            if not acquired:
                logger.info("clustering lock busy; will retry", extra={"problem": problem_pk})
                return None
            return self._attach(problem, match)

    @transaction.atomic
    def _attach(self, problem: Problem, match) -> IssueCluster | None:
        problem.refresh_from_db(fields=["cluster_id"])
        if problem.cluster_id:
            return None

        partner = (
            Problem.objects.select_related("category").filter(pk=match.candidate.problem_id).first()
        )
        if partner is None:
            return None

        cluster = partner.cluster
        if cluster is None:
            cluster = IssueCluster.objects.create(
                title=partner.title[:250],
                description=partner.description[:4000],
                category=partner.category,
                department=partner.department,
                primary_problem=partner,
                address=partner.address,
                city=partner.city,
                district=partner.district,
                state=partner.state,
                pincode=partner.pincode,
                latitude=partner.latitude,
                longitude=partner.longitude,
                review_required=match.needs_review,
            )
            self._add_member(cluster, partner, match, method="GEOGRAPHIC")

        self._add_member(cluster, problem, match, method="GEOGRAPHIC")
        self.recount(cluster)

        ProblemTimelineEvent.objects.create(
            problem=problem,
            kind=ProblemTimelineEvent.Kind.CLUSTERED,
            title="Grouped with similar reports",
            description=(
                f"This report was grouped with {cluster.problem_count - 1} similar report(s) "
                "so the department sees one issue. Your report is preserved in full."
            ),
            actor_label="Duplicate detection",
            metadata={
                "cluster_id": str(cluster.public_id),
                "confidence": match.score,
                "distance_metres": match.distance_metres,
                "needs_review": match.needs_review,
            },
        )
        logger.info(
            "problem clustered",
            extra={
                "problem": problem.pk,
                "cluster": cluster.pk,
                "score": match.score,
                "review": match.needs_review,
            },
        )
        return cluster

    @staticmethod
    def _add_member(cluster: IssueCluster, problem: Problem, match, method: str) -> None:
        ClusterMembership.objects.get_or_create(
            cluster=cluster,
            problem=problem,
            defaults={
                "method": method,
                "confidence": match.score,
                "distance_metres": match.distance_metres,
                "title_similarity": match.title_similarity,
            },
        )
        Problem.objects.filter(pk=problem.pk).update(cluster=cluster)
        problem.cluster_id = cluster.id

    @staticmethod
    def recount(cluster: IssueCluster) -> None:
        """Recompute cluster aggregates from the member rows.

        Derived from the source of truth rather than incremented, so a retry or
        a manual merge cannot leave the counts drifting.
        """
        stats = Problem.objects.filter(cluster=cluster).aggregate(
            problems=Count("id"),
            support=Sum("support_count"),
            reporters=Count("reporter_id", distinct=True),
        )
        values = {
            "problem_count": stats["problems"] or 0,
            "total_support_count": stats["support"] or 0,
            "unique_reporter_count": stats["reporters"] or 0,
        }
        IssueCluster.objects.filter(pk=cluster.pk).update(**values)
        # `.update()` writes the row but leaves the caller holding a stale
        # object, so mirror the new values onto the instance being returned.
        for field, value in values.items():
            setattr(cluster, field, value)

    def merge_manually(self, cluster: IssueCluster, problem: Problem, actor) -> None:
        """A moderator explicitly places a report into a cluster."""
        ClusterMembership.objects.update_or_create(
            cluster=cluster,
            problem=problem,
            defaults={
                "method": ClusterMembership.Method.MANUAL,
                "confidence": 1.0,
                "confirmed_by": actor,
                "confirmed_at": timezone.now(),
            },
        )
        Problem.objects.filter(pk=problem.pk).update(cluster=cluster)
        self.recount(cluster)

    def detach(self, problem: Problem) -> None:
        """Undo a wrong merge. The report returns to standing on its own."""
        # Read the membership from the database rather than from the caller's
        # instance: membership is written with `.update()`, so an object the
        # caller has held across the merge can still say `cluster_id is None`.
        cluster_id = (
            Problem.objects.filter(pk=problem.pk).values_list("cluster_id", flat=True).first()
        )
        ClusterMembership.objects.filter(problem=problem).delete()
        Problem.objects.filter(pk=problem.pk).update(cluster=None)
        problem.cluster_id = None

        if cluster_id:
            cluster = IssueCluster.objects.filter(pk=cluster_id).first()
            if cluster:
                self.recount(cluster)


clustering_service = IssueClusteringService()

"""Background clustering. Idempotent and retry-safe by construction."""

from __future__ import annotations

import logging

from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_kwargs={"max_retries": 3},
    ignore_result=True,
)
def detect_duplicates_task(self, problem_pk: int) -> str:
    """Score a new report against nearby recent ones and cluster if it matches.

    Safe to run twice: `process` returns immediately when the problem already
    belongs to a cluster.
    """
    from .application.service import clustering_service

    cluster = clustering_service.process(problem_pk)
    return f"clustered:{cluster.pk}" if cluster else "no-match"


@shared_task(ignore_result=True)
def recount_clusters_task() -> int:
    """Nightly reconciliation of cluster aggregates against the member rows."""
    from .application.service import clustering_service
    from .models import ClusterStatus, IssueCluster

    clusters = IssueCluster.objects.filter(status=ClusterStatus.ACTIVE)
    for cluster in clusters.iterator(chunk_size=200):
        clustering_service.recount(cluster)
    return clusters.count()

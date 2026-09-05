"""Clustering subscribes to problem creation.

The handler only enqueues. Duplicate detection scores up to 200 candidates, so
running it inline would put similarity search on the path of a citizen pressing
Submit -- exactly what section 51 says not to do.
"""

from __future__ import annotations

import logging

from jandrishti.shared.domain.events import DomainEvent, Events
from jandrishti.shared.infrastructure.event_bus import subscribe

logger = logging.getLogger(__name__)


@subscribe(Events.PROBLEM_CREATED)
def enqueue_duplicate_detection(event: DomainEvent) -> None:
    from .tasks import detect_duplicates_task

    problem_pk = event.payload.get("problem_pk")
    if problem_pk is None:
        return
    detect_duplicates_task.delay(problem_pk)


@subscribe(Events.PROBLEM_SUPPORTED)
def refresh_cluster_totals(event: DomainEvent) -> None:
    """Keep the cluster headline figure honest as supports arrive."""
    from jandrishti.modules.problems.models import Problem

    from .application.service import clustering_service

    cluster_id = (
        Problem.objects.filter(pk=event.payload.get("problem_pk"))
        .values_list("cluster_id", flat=True)
        .first()
    )
    if not cluster_id:
        return
    from .models import IssueCluster

    cluster = IssueCluster.objects.filter(pk=cluster_id).first()
    if cluster:
        clustering_service.recount(cluster)

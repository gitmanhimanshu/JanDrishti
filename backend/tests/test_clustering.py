"""
Issue clustering against the database (spec 19).

The load-bearing assertion in this file is that clustering never destroys a
citizen report: after a merge, every original row is still present, still
attributed and still individually addressable.
"""

from __future__ import annotations

import pytest

from jandrishti.modules.issue_clustering.application.service import clustering_service
from jandrishti.modules.issue_clustering.models import ClusterMembership, IssueCluster
from jandrishti.modules.problems.models import Problem

pytestmark = pytest.mark.django_db

POTHOLE = {
    "title": "Deep pothole at the school gate on Kalyani Nagar road",
    "description": (
        "A large pothole has opened right at the school gate and two-wheelers "
        "are losing control on it every morning."
    ),
    "state": "Maharashtra",
    "district": "Pune",
    "city": "Pune",
}


def make_problem(reporter, category, *, title=None, lat=18.5204, lng=73.8567, **extra) -> Problem:
    return Problem.objects.create(
        title=title or POTHOLE["title"],
        description=extra.pop("description", POTHOLE["description"]),
        reporter=reporter,
        category=category,
        state=POTHOLE["state"],
        district=POTHOLE["district"],
        city=POTHOLE["city"],
        latitude=lat,
        longitude=lng,
        **extra,
    )


class TestClustering:
    def test_two_near_identical_reports_form_one_cluster(self, make_user, category):
        first = make_problem(make_user(), category)
        second = make_problem(
            make_user(),
            category,
            title="Pothole outside the school gate is dangerous",
            lat=18.52045,
            lng=73.85675,
        )

        cluster = clustering_service.process(second.pk)

        assert cluster is not None
        assert cluster.problem_count == 2
        first.refresh_from_db()
        second.refresh_from_db()
        assert first.cluster_id == second.cluster_id == cluster.id

    def test_every_original_report_survives_the_merge(self, make_user, category):
        """The rule the spec states outright: do not delete the originals."""
        reporters = [make_user() for _ in range(5)]
        problems = [
            make_problem(
                reporter,
                category,
                title=f"Pothole near the school gate, report {index}",
                lat=18.5204 + index * 0.00001,
            )
            for index, reporter in enumerate(reporters)
        ]
        for problem in problems[1:]:
            clustering_service.process(problem.pk)

        assert Problem.objects.count() == 5
        for problem, reporter in zip(problems, reporters):
            problem.refresh_from_db()
            assert problem.reporter_id == reporter.id
            assert Problem.objects.filter(public_id=problem.public_id).exists()

    def test_the_aggregate_counts_distinct_reporters(self, make_user, category):
        for index in range(4):
            problem = make_problem(
                make_user(), category, title=f"Pothole at the school gate {index}"
            )
            clustering_service.process(problem.pk)

        cluster = IssueCluster.objects.get()
        assert cluster.problem_count == 4
        assert cluster.unique_reporter_count == 4
        assert "4 people" in cluster.aggregate_label

    def test_distant_reports_do_not_merge(self, make_user, category):
        """Same words, different city -- the failure that would be worst."""
        make_problem(make_user(), category)
        delhi = make_problem(make_user(), category, lat=28.6139, lng=77.2090)

        assert clustering_service.process(delhi.pk) is None
        delhi.refresh_from_db()
        assert delhi.cluster_id is None

    def test_unrelated_nearby_reports_do_not_merge(self, make_user, category):
        make_problem(make_user(), category)
        unrelated = make_problem(
            make_user(),
            category,
            title="Garbage has not been collected for eleven days",
            description="The bins near the housing society are overflowing onto the road.",
        )
        assert clustering_service.process(unrelated.pk) is None

    def test_processing_is_idempotent(self, make_user, category):
        """A retried Celery task must not double-count."""
        make_problem(make_user(), category)
        second = make_problem(
            make_user(), category, title="Pothole outside the school gate is dangerous"
        )

        clustering_service.process(second.pk)
        clustering_service.process(second.pk)
        clustering_service.process(second.pk)

        assert IssueCluster.objects.count() == 1
        assert IssueCluster.objects.get().problem_count == 2
        assert ClusterMembership.objects.filter(problem=second).count() == 1

    def test_a_clustered_report_gets_a_timeline_entry(self, make_user, category):
        make_problem(make_user(), category)
        second = make_problem(
            make_user(), category, title="Pothole outside the school gate is dangerous"
        )
        clustering_service.process(second.pk)

        entry = second.timeline.filter(kind="CLUSTERED").first()
        assert entry is not None
        assert "preserved" in entry.description

    def test_detach_undoes_a_wrong_merge(self, make_user, category):
        make_problem(make_user(), category)
        second = make_problem(
            make_user(), category, title="Pothole outside the school gate is dangerous"
        )
        cluster = clustering_service.process(second.pk)
        assert cluster.problem_count == 2

        clustering_service.detach(second)

        second.refresh_from_db()
        cluster.refresh_from_db()
        assert second.cluster_id is None
        assert cluster.problem_count == 1

    def test_cluster_totals_include_every_members_support(self, make_user, category):
        first = make_problem(make_user(), category)
        second = make_problem(
            make_user(), category, title="Pothole outside the school gate is dangerous"
        )
        Problem.objects.filter(pk=first.pk).update(support_count=30)
        Problem.objects.filter(pk=second.pk).update(support_count=12)

        cluster = clustering_service.process(second.pk)
        cluster.refresh_from_db()
        assert cluster.total_support_count == 42


class TestClusterApi:
    def test_cluster_detail_lists_the_individual_reports(self, api, make_user, category):
        make_problem(make_user(), category)
        second = make_problem(
            make_user(), category, title="Pothole outside the school gate is dangerous"
        )
        cluster = clustering_service.process(second.pk)

        data = api.get(f"/api/v1/clusters/{cluster.public_id}/").json()["data"]
        assert data["problem_count"] == 2
        assert len(data["problems"]) == 2

    def test_only_a_moderator_can_merge_manually(self, auth_client, make_user, category):
        problem = make_problem(make_user(), category)
        cluster = IssueCluster.objects.create(title="Potholes near the school", category=category)
        response = auth_client.post(
            f"/api/v1/clusters/{cluster.public_id}/merge/",
            {"problem_id": str(problem.public_id)},
            format="json",
        )
        assert response.status_code == 403

    def test_moderator_merge_is_audited(self, as_user, moderator, make_user, category):
        from jandrishti.modules.audit.models import AuditLog

        problem = make_problem(make_user(), category)
        cluster = IssueCluster.objects.create(title="Potholes near the school", category=category)
        response = as_user(moderator).post(
            f"/api/v1/clusters/{cluster.public_id}/merge/",
            {"problem_id": str(problem.public_id)},
            format="json",
        )
        assert response.status_code == 200
        assert AuditLog.objects.filter(action="cluster.manual_merge").exists()

"""
Pure domain tests. No database, no HTTP -- these run in milliseconds, which is
the practical payoff of keeping the rules out of the views.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from jandrishti.modules.experience.domain.credibility import (
    CredibilityInputs,
    compute_credibility,
)
from jandrishti.modules.issue_clustering.domain.detection import (
    Candidate,
    distance_component,
    score_candidate,
)
from jandrishti.modules.problems.domain.enums import ProblemStatus
from jandrishti.modules.problems.domain.lifecycle import (
    assert_actor_may_set,
    problem_lifecycle,
)
from jandrishti.modules.problems.domain.ranking import compute_trend_score
from jandrishti.shared.domain.exceptions import (
    IllegalStateTransitionError,
    PermissionDeniedError,
    ValidationError,
)
from jandrishti.shared.domain.value_objects import GeoPoint, Location, Money
from jandrishti.shared.infrastructure.text import similarity


class TestGeoPoint:
    def test_rejects_impossible_coordinates(self):
        with pytest.raises(ValidationError):
            GeoPoint(95.0, 0.0)
        with pytest.raises(ValidationError):
            GeoPoint(0.0, 200.0)

    def test_distance_between_known_cities(self):
        pune = GeoPoint(18.5204, 73.8567)
        mumbai = GeoPoint(19.0760, 72.8777)
        # Real great-circle distance is about 120 km.
        assert 115 < pune.distance_km(mumbai) < 125

    def test_bounding_box_contains_the_point(self):
        point = GeoPoint(18.5204, 73.8567)
        min_lat, max_lat, min_lng, max_lng = point.bounding_box(1.0)
        assert min_lat < point.latitude < max_lat
        assert min_lng < point.longitude < max_lng

    def test_bounding_box_stays_finite_near_the_pole(self):
        """The cos(latitude) term goes to zero at the pole; it must be clamped."""
        min_lat, max_lat, min_lng, max_lng = GeoPoint(89.999, 0.0).bounding_box(5.0)
        assert -180.0 <= min_lng <= max_lng <= 180.0
        assert max_lat <= 90.0


class TestLocation:
    def test_requires_state_or_coordinates(self):
        with pytest.raises(ValidationError):
            Location(city="Pune")

    def test_accepts_coordinates_without_state(self):
        assert Location(point=GeoPoint(18.5, 73.8)).point is not None

    def test_rejects_malformed_pincode(self):
        with pytest.raises(ValidationError):
            Location(state="Maharashtra", pincode="01234")


class TestMoney:
    def test_rejects_negative(self):
        with pytest.raises(ValidationError):
            Money.of("-1")

    def test_arithmetic_is_exact(self):
        assert (Money.of("0.1") + Money.of("0.2")).amount == Money.of("0.3").amount


class TestProblemLifecycle:
    def test_happy_path_is_allowed(self):
        assert problem_lifecycle.can(ProblemStatus.SUBMITTED, ProblemStatus.UNDER_REVIEW)
        assert problem_lifecycle.can(ProblemStatus.COMPLETED, ProblemStatus.RESOLVED)

    def test_cannot_skip_from_submitted_to_resolved(self):
        with pytest.raises(IllegalStateTransitionError):
            problem_lifecycle.assert_can(ProblemStatus.SUBMITTED, ProblemStatus.RESOLVED)

    def test_resolved_is_terminal(self):
        assert problem_lifecycle.is_terminal(ProblemStatus.RESOLVED)
        assert problem_lifecycle.allowed_from(ProblemStatus.RESOLVED) == frozenset()

    def test_error_reports_the_allowed_moves(self):
        with pytest.raises(IllegalStateTransitionError) as exc:
            problem_lifecycle.assert_can(ProblemStatus.SUBMITTED, ProblemStatus.RESOLVED)
        assert "allowed" in exc.value.details

    def test_verification_can_send_work_back(self):
        """Proof that does not hold up must not quietly close the issue."""
        assert problem_lifecycle.can(ProblemStatus.VERIFICATION, ProblemStatus.WORK_IN_PROGRESS)

    def test_no_self_transition(self):
        with pytest.raises(IllegalStateTransitionError):
            problem_lifecycle.assert_can(ProblemStatus.ACKNOWLEDGED, ProblemStatus.ACKNOWLEDGED)


class FakeUser:
    def __init__(self, role: str):
        self.role = role
        self.is_superuser = False


class TestStatusAuthorization:
    def test_department_cannot_declare_its_own_issue_resolved(self):
        with pytest.raises(PermissionDeniedError):
            assert_actor_may_set(FakeUser("GOVERNMENT_OFFICIAL"), ProblemStatus.RESOLVED)

    def test_department_can_report_progress(self):
        assert_actor_may_set(FakeUser("GOVERNMENT_OFFICIAL"), ProblemStatus.WORK_STARTED)

    def test_moderator_can_resolve(self):
        assert_actor_may_set(FakeUser("MODERATOR"), ProblemStatus.RESOLVED)

    def test_citizen_can_change_nothing(self):
        with pytest.raises(PermissionDeniedError):
            assert_actor_may_set(FakeUser("CITIZEN"), ProblemStatus.UNDER_REVIEW)


class TestTrendScore:
    def test_recent_engagement_outranks_old_popularity(self):
        now = datetime.now(UTC)
        fresh = compute_trend_score(
            support_count=40,
            report_count=0,
            comment_count=0,
            last_activity_at=now - timedelta(hours=2),
            now=now,
        )
        stale = compute_trend_score(
            support_count=300,
            report_count=0,
            comment_count=0,
            last_activity_at=now - timedelta(days=400),
            now=now,
        )
        assert fresh > stale

    def test_independent_reports_weigh_more_than_supports(self):
        now = datetime.now(UTC)
        common = {"last_activity_at": now, "now": now, "comment_count": 0}
        reported = compute_trend_score(support_count=0, report_count=10, **common)
        supported = compute_trend_score(support_count=10, report_count=0, **common)
        assert reported > supported

    def test_zero_engagement_is_zero(self):
        now = datetime.now(UTC)
        assert (
            compute_trend_score(
                support_count=0, report_count=0, comment_count=0, last_activity_at=now, now=now
            )
            == 0.0
        )


class TestDuplicateDetection:
    BASE = {
        "new_title": "Large pothole near the school gate",
        "new_description": "Deep pothole causing accidents every morning.",
        "new_category_id": 1,
        "new_created_at": datetime(2026, 1, 10, tzinfo=UTC),
        "radius_metres": 150.0,
        "window_days": 180,
    }

    def _candidate(self, **overrides) -> Candidate:
        defaults: dict = dict(  # noqa: C408 - keyword form reads better for a fixture
            problem_id=2,
            title="Pothole at the school gate is dangerous",
            description="There is a deep pothole right outside the school.",
            category_id=1,
            latitude=18.5204,
            longitude=73.8567,
            created_at=datetime(2026, 1, 8, tzinfo=UTC),
        )
        return Candidate(**{**defaults, **overrides})

    def test_same_place_and_wording_scores_high(self):
        score = score_candidate(
            new_point=GeoPoint(18.52042, 73.85672), candidate=self._candidate(), **self.BASE
        )
        assert score.score >= 0.62

    def test_same_words_far_apart_does_not_merge(self):
        """The failure mode that matters: identical wording in another city."""
        score = score_candidate(
            new_point=GeoPoint(28.6139, 77.2090),  # Delhi vs Pune
            candidate=self._candidate(),
            **self.BASE,
        )
        assert not score.should_auto_merge
        assert score.score < 0.62

    def test_different_category_lowers_the_score(self):
        near = score_candidate(
            new_point=GeoPoint(18.5204, 73.8567), candidate=self._candidate(), **self.BASE
        )
        other_category = score_candidate(
            new_point=GeoPoint(18.5204, 73.8567),
            candidate=self._candidate(category_id=99),
            **self.BASE,
        )
        assert other_category.score < near.score

    def test_missing_coordinates_is_neutral_not_disqualifying(self):
        assert distance_component(None, 150.0) == 0.5

    def test_unrelated_text_nearby_does_not_auto_merge(self):
        score = score_candidate(
            new_point=GeoPoint(18.5204, 73.8567),
            candidate=self._candidate(
                title="Streetlight has been out for three weeks",
                description="The lamp post opposite the temple is dark.",
            ),
            **self.BASE,
        )
        assert not score.should_auto_merge


class TestTextSimilarity:
    def test_word_order_does_not_matter_much(self):
        assert similarity("broken road near market", "road broken at the market") > 0.6

    def test_unrelated_text_scores_low(self):
        assert similarity("garbage not collected", "hospital has no doctors") < 0.3


class TestCredibility:
    def _inputs(self, **overrides) -> CredibilityInputs:
        defaults: dict = dict(  # noqa: C408 - keyword form reads better for a fixture
            author_verified=False,
            author_category="",
            domain_matches_category=False,
            years_of_experience=0,
            evidence_count=0,
            linked_problem_count=0,
            support_count=0,
            comment_count=0,
            has_root_cause=False,
            has_implementation=False,
            has_expected_impact=False,
            has_cost_estimate=False,
        )
        return CredibilityInputs(**{**defaults, **overrides})

    def test_support_alone_cannot_dominate(self):
        """The central rule of spec 31: support is a signal, not proof."""
        popular_but_empty = compute_credibility(self._inputs(support_count=10_000))
        thorough_but_quiet = compute_credibility(
            self._inputs(
                author_verified=True,
                author_category="DOMAIN_EXPERT",
                domain_matches_category=True,
                evidence_count=4,
                has_root_cause=True,
                has_implementation=True,
                has_expected_impact=True,
                has_cost_estimate=True,
            )
        )
        assert thorough_but_quiet > popular_but_empty

    def test_verification_raises_the_score(self):
        assert compute_credibility(
            self._inputs(author_verified=True, author_category="GOVERNMENT_EMPLOYEE")
        ) > compute_credibility(self._inputs())

    def test_actionable_detail_raises_the_score(self):
        assert compute_credibility(
            self._inputs(has_root_cause=True, has_implementation=True)
        ) > compute_credibility(self._inputs())

    def test_score_is_bounded(self):
        maxed = compute_credibility(
            self._inputs(
                author_verified=True,
                author_category="DOMAIN_EXPERT",
                domain_matches_category=True,
                years_of_experience=40,
                evidence_count=50,
                linked_problem_count=50,
                support_count=100_000,
                comment_count=1000,
                has_root_cause=True,
                has_implementation=True,
                has_expected_impact=True,
                has_cost_estimate=True,
            )
        )
        assert 0 <= maxed <= 100

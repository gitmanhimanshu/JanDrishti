"""Problem creation, support concurrency, lifecycle and authorization."""

from __future__ import annotations

import pytest

from jandrishti.modules.accounts.domain.enums import UserRole
from jandrishti.modules.problems.application.use_cases import (
    SupportProblemCommand,
    SupportProblemUseCase,
    UpdateProblemStatusCommand,
    UpdateProblemStatusUseCase,
)
from jandrishti.modules.problems.domain.enums import ProblemStatus
from jandrishti.modules.problems.models import Problem, ProblemSupport, ProblemTimelineEvent
from jandrishti.shared.application.use_case import Actor
from jandrishti.shared.domain.exceptions import (
    IllegalStateTransitionError,
    PermissionDeniedError,
)

pytestmark = pytest.mark.django_db

VALID_PROBLEM = {
    "title": "Streetlight outside the primary school has been dark for weeks",
    "description": (
        "The streetlight at the school gate stopped working three weeks ago. "
        "Children walking home after evening tuition have no light at all."
    ),
    "state": "Maharashtra",
    "district": "Pune",
    "city": "Pune",
    "latitude": 18.5204,
    "longitude": 73.8567,
}


class TestCreateProblem:
    def test_creates_and_returns_the_problem(self, auth_client, category, routing_rule):
        response = auth_client.post(
            "/api/v1/problems/create/",
            {**VALID_PROBLEM, "category_id": str(category.public_id)},
            format="json",
        )
        assert response.status_code == 201
        data = response.json()["data"]
        assert data["title"] == VALID_PROBLEM["title"]
        assert data["support_count"] == 0

    def test_routes_to_a_department_automatically(self, auth_client, category, routing_rule):
        response = auth_client.post(
            "/api/v1/problems/create/",
            {**VALID_PROBLEM, "category_id": str(category.public_id)},
            format="json",
        )
        data = response.json()["data"]
        assert data["department"]["name"] == "Road Department"
        assert data["status"] == ProblemStatus.DEPARTMENT_ASSIGNED

    def test_unrouted_report_still_succeeds(self, auth_client, category):
        """No routing rule must not mean no report."""
        response = auth_client.post(
            "/api/v1/problems/create/",
            {**VALID_PROBLEM, "category_id": str(category.public_id)},
            format="json",
        )
        assert response.status_code == 201
        assert response.json()["data"]["status"] == ProblemStatus.SUBMITTED

    def test_rejects_a_thin_description(self, auth_client):
        response = auth_client.post(
            "/api/v1/problems/create/", {**VALID_PROBLEM, "description": "broken"}, format="json"
        )
        assert response.status_code == 400
        assert response.json()["error"]["code"] == "VALIDATION_ERROR"

    def test_requires_a_location(self, auth_client):
        payload = {
            k: v for k, v in VALID_PROBLEM.items() if k not in {"state", "latitude", "longitude"}
        }
        assert (
            auth_client.post("/api/v1/problems/create/", payload, format="json").status_code == 400
        )

    def test_rejects_impossible_coordinates(self, auth_client):
        response = auth_client.post(
            "/api/v1/problems/create/", {**VALID_PROBLEM, "latitude": 999}, format="json"
        )
        assert response.status_code == 400

    def test_writes_an_opening_timeline_entry(self, auth_client, category):
        response = auth_client.post(
            "/api/v1/problems/create/",
            {**VALID_PROBLEM, "category_id": str(category.public_id)},
            format="json",
        )
        problem = Problem.objects.get(public_id=response.json()["data"]["id"])
        assert problem.timeline.filter(kind=ProblemTimelineEvent.Kind.REPORTED).exists()

    def test_anonymous_report_hides_the_name_but_keeps_the_account(self, auth_client, citizen):
        response = auth_client.post(
            "/api/v1/problems/create/",
            {**VALID_PROBLEM, "is_anonymous_report": True},
            format="json",
        )
        data = response.json()["data"]
        assert data["reporter"]["is_anonymous"] is True
        assert data["reporter"]["display_name"] == "Citizen"
        # Accountability is preserved internally.
        assert Problem.objects.get(public_id=data["id"]).reporter_id == citizen.id


class TestSupport:
    def test_support_increments_the_counter(self, as_user, other_citizen, problem):
        response = as_user(other_citizen).post(
            f"/api/v1/problems/{problem.public_id}/support/", {}, format="json"
        )
        assert response.status_code == 200
        assert response.json()["data"]["support_count"] == 1

    def test_supporting_twice_is_idempotent(self, as_user, other_citizen, problem):
        client = as_user(other_citizen)
        client.post(f"/api/v1/problems/{problem.public_id}/support/", {}, format="json")
        second = client.post(f"/api/v1/problems/{problem.public_id}/support/", {}, format="json")

        assert second.json()["data"]["already_supported"] is True
        assert second.json()["data"]["support_count"] == 1
        assert ProblemSupport.objects.filter(problem=problem).count() == 1

    def test_counter_matches_the_row_count_after_many_supporters(self, make_user, problem):
        """The cached counter must agree with the constraint-backed truth."""
        for _ in range(25):
            SupportProblemUseCase().execute(
                SupportProblemCommand(
                    problem_id=str(problem.public_id), actor=Actor(user=make_user())
                )
            )
        problem.refresh_from_db()
        assert problem.support_count == ProblemSupport.objects.filter(problem=problem).count() == 25

    def test_withdrawal_never_drives_the_counter_negative(self, as_user, other_citizen, problem):
        client = as_user(other_citizen)
        client.delete(f"/api/v1/problems/{problem.public_id}/support/")
        problem.refresh_from_db()
        assert problem.support_count == 0

    def test_withdrawal_decrements(self, as_user, other_citizen, problem):
        client = as_user(other_citizen)
        client.post(f"/api/v1/problems/{problem.public_id}/support/", {}, format="json")
        response = client.delete(f"/api/v1/problems/{problem.public_id}/support/")
        assert response.json()["data"]["support_count"] == 0

    def test_viewer_support_state_is_reported(self, as_user, other_citizen, problem):
        client = as_user(other_citizen)
        client.post(f"/api/v1/problems/{problem.public_id}/support/", {}, format="json")
        data = client.get(f"/api/v1/problems/{problem.public_id}/").json()["data"]
        assert data["viewer_has_supported"] is True

    def test_anonymous_viewer_sees_no_support_state(self, api, problem):
        data = api.get(f"/api/v1/problems/{problem.public_id}/").json()["data"]
        assert data["viewer_has_supported"] is False


class TestStatusTransitions:
    def test_official_can_acknowledge_an_assigned_problem(self, official, problem):
        problem.status = ProblemStatus.DEPARTMENT_ASSIGNED
        problem.save(update_fields=["status"])

        updated = UpdateProblemStatusUseCase().execute(
            UpdateProblemStatusCommand(
                problem_id=str(problem.public_id),
                to_status=ProblemStatus.ACKNOWLEDGED,
                actor=Actor(user=official),
            )
        )
        assert updated.status == ProblemStatus.ACKNOWLEDGED
        assert updated.acknowledged_at is not None

    def test_illegal_jump_is_refused(self, official, problem):
        """COMPLETED is a status this official may set -- but not from here."""
        problem.status = ProblemStatus.DEPARTMENT_ASSIGNED
        problem.save(update_fields=["status"])
        with pytest.raises(IllegalStateTransitionError):
            UpdateProblemStatusUseCase().execute(
                UpdateProblemStatusCommand(
                    problem_id=str(problem.public_id),
                    to_status=ProblemStatus.COMPLETED,
                    actor=Actor(user=official),
                )
            )

    def test_department_cannot_resolve_its_own_issue(self, official, problem):
        """Authorization is checked before the transition, so this is a 403.

        A department declaring its own work resolved without review is the
        thing the role split exists to prevent (spec 33).
        """
        problem.status = ProblemStatus.COMPLETED
        problem.save(update_fields=["status"])
        with pytest.raises(PermissionDeniedError):
            UpdateProblemStatusUseCase().execute(
                UpdateProblemStatusCommand(
                    problem_id=str(problem.public_id),
                    to_status=ProblemStatus.RESOLVED,
                    actor=Actor(user=official),
                )
            )

    def test_citizen_cannot_change_status(self, citizen, problem):
        with pytest.raises(PermissionDeniedError):
            UpdateProblemStatusUseCase().execute(
                UpdateProblemStatusCommand(
                    problem_id=str(problem.public_id),
                    to_status=ProblemStatus.UNDER_REVIEW,
                    actor=Actor(user=citizen),
                )
            )

    def test_official_from_another_department_is_refused(self, make_user, problem, department):
        """Object-level authorization: role alone is not enough."""
        from jandrishti.modules.catalog.models import Department
        from jandrishti.modules.government.models import DepartmentMembership

        other_department = Department.objects.create(name="Water Department", level="MUNICIPAL")
        outsider = make_user(role=UserRole.GOVERNMENT_OFFICIAL)
        DepartmentMembership.objects.create(user=outsider, department=other_department)

        problem.status = ProblemStatus.DEPARTMENT_ASSIGNED
        problem.save(update_fields=["status"])

        with pytest.raises(PermissionDeniedError):
            UpdateProblemStatusUseCase().execute(
                UpdateProblemStatusCommand(
                    problem_id=str(problem.public_id),
                    to_status=ProblemStatus.ACKNOWLEDGED,
                    actor=Actor(user=outsider),
                )
            )

    def test_status_change_is_recorded_on_the_timeline(self, official, problem):
        problem.status = ProblemStatus.DEPARTMENT_ASSIGNED
        problem.save(update_fields=["status"])
        UpdateProblemStatusUseCase().execute(
            UpdateProblemStatusCommand(
                problem_id=str(problem.public_id),
                to_status=ProblemStatus.ACKNOWLEDGED,
                note="Inspection scheduled.",
                actor=Actor(user=official),
            )
        )
        event = problem.timeline.filter(kind=ProblemTimelineEvent.Kind.STATUS_CHANGED).latest(
            "created_at"
        )
        assert event.from_status == ProblemStatus.DEPARTMENT_ASSIGNED
        assert event.to_status == ProblemStatus.ACKNOWLEDGED

    def test_status_change_is_audited(self, official, problem):
        from jandrishti.modules.audit.models import AuditLog

        problem.status = ProblemStatus.DEPARTMENT_ASSIGNED
        problem.save(update_fields=["status"])
        UpdateProblemStatusUseCase().execute(
            UpdateProblemStatusCommand(
                problem_id=str(problem.public_id),
                to_status=ProblemStatus.ACKNOWLEDGED,
                actor=Actor(user=official),
            )
        )
        assert AuditLog.objects.filter(action="problem.status_changed").exists()


class TestRankingTabs:
    def test_every_tab_returns_a_valid_page(self, api, problem):
        for tab in (
            "trending",
            "most_supported",
            "most_reported",
            "high_priority",
            "recent",
            "recently_updated",
            "resolved",
            "stale",
        ):
            response = api.get(f"/api/v1/problems/?tab={tab}")
            assert response.status_code == 200, tab

    def test_nearby_without_coordinates_falls_back_rather_than_erroring(self, api, problem):
        response = api.get("/api/v1/problems/?tab=nearby")
        assert response.status_code == 200
        assert len(response.json()["data"]) == 1

    def test_nearby_filters_by_distance(self, api, problem, citizen, category):
        Problem.objects.create(
            title="Unrelated issue very far away in another state entirely",
            description="A long way from the first problem, so it must not appear nearby.",
            reporter=citizen,
            category=category,
            state="Delhi",
            latitude=28.6139,
            longitude=77.2090,
        )
        response = api.get("/api/v1/problems/?tab=nearby&lat=18.5204&lng=73.8567&radius_km=5")
        titles = [row["title"] for row in response.json()["data"]]
        assert problem.title in titles
        assert len(titles) == 1

    def test_unknown_tab_falls_back_to_trending(self, api, problem):
        assert api.get("/api/v1/problems/?tab=nonsense").status_code == 200


class TestFiltering:
    def test_parent_category_includes_the_subtree(self, api, problem, category):
        parent = category.parent
        response = api.get(f"/api/v1/problems/?category={parent.public_id}")
        assert len(response.json()["data"]) == 1

    def test_state_filter(self, api, problem):
        assert len(api.get("/api/v1/problems/?state=Maharashtra").json()["data"]) == 1
        assert len(api.get("/api/v1/problems/?state=Kerala").json()["data"]) == 0

    def test_text_search(self, api, problem):
        assert len(api.get("/api/v1/problems/?q=pothole").json()["data"]) == 1
        assert len(api.get("/api/v1/problems/?q=zebra").json()["data"]) == 0

"""
The public-first contract (spec 4 and 5).

These are the tests that would fail if someone ever wrapped the read endpoints
in a login requirement, or forgot to gate a write.
"""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.django_db

PUBLIC_READ_PATHS = [
    "/api/v1/problems/",
    "/api/v1/problems/tabs/",
    "/api/v1/experiences/",
    "/api/v1/projects/",
    "/api/v1/categories/",
    "/api/v1/departments/",
    "/api/v1/states/",
    "/api/v1/clusters/",
    "/api/v1/stats/public/",
    "/api/v1/stats/departments/",
    "/api/v1/search/?q=road",
    "/api/v1/funding/campaigns/",
]


class TestAnonymousCanRead:
    @pytest.mark.parametrize("path", PUBLIC_READ_PATHS)
    def test_public_endpoints_need_no_login(self, api, path):
        assert api.get(path).status_code == 200, path

    def test_problem_detail_is_public(self, api, problem):
        response = api.get(f"/api/v1/problems/{problem.public_id}/")
        assert response.status_code == 200
        assert response.json()["data"]["title"] == problem.title

    def test_comment_thread_is_public(self, api, problem):
        response = api.get(f"/api/v1/comments/PROBLEM/{problem.public_id}/")
        assert response.status_code == 200

    def test_public_profile_is_readable(self, api, citizen):
        assert api.get(f"/api/v1/users/{citizen.id}/").status_code == 200


class TestAnonymousCannotWrite:
    """Every one of these must be 401, never a silent success."""

    def test_cannot_report_a_problem(self, api):
        response = api.post("/api/v1/problems/create/", {"title": "x" * 20}, format="json")
        assert response.status_code == 401

    def test_cannot_support(self, api, problem):
        response = api.post(f"/api/v1/problems/{problem.public_id}/support/", {}, format="json")
        assert response.status_code == 401

    def test_cannot_comment(self, api, problem):
        response = api.post(
            "/api/v1/comments/",
            {"target_type": "PROBLEM", "target_id": str(problem.public_id), "body": "hello"},
            format="json",
        )
        assert response.status_code == 401

    def test_cannot_publish_experience(self, api):
        assert api.post("/api/v1/experiences/create/", {}, format="json").status_code == 401

    def test_cannot_bookmark(self, api, problem):
        response = api.post(
            "/api/v1/social/bookmarks/toggle/",
            {"target_type": "PROBLEM", "target_id": str(problem.public_id)},
            format="json",
        )
        assert response.status_code == 401

    def test_cannot_read_notifications(self, api):
        assert api.get("/api/v1/notifications/").status_code == 401

    def test_cannot_reach_the_government_dashboard(self, api):
        assert api.get("/api/v1/government/dashboard/").status_code == 401

    def test_cannot_read_the_audit_log(self, api):
        assert api.get("/api/v1/audit/").status_code == 401


class TestErrorEnvelope:
    def test_errors_use_the_documented_shape(self, api):
        response = api.get("/api/v1/problems/00000000-0000-0000-0000-000000000000/")
        assert response.status_code == 404
        body = response.json()
        assert body["success"] is False
        assert body["error"]["code"] == "NOT_FOUND"
        assert isinstance(body["error"]["message"], str)

    def test_success_responses_are_enveloped(self, api):
        body = api.get("/api/v1/stats/public/").json()
        assert body["success"] is True
        assert "data" in body

    def test_lists_are_paginated_with_meta(self, api):
        body = api.get("/api/v1/problems/").json()
        assert "meta" in body
        assert {"count", "page", "page_size", "total_pages"} <= set(body["meta"])


class TestStatsAreHonest:
    def test_empty_platform_reports_zeros_not_invented_numbers(self, api):
        data = api.get("/api/v1/stats/public/").json()["data"]
        assert data["problems_reported"] == 0
        assert data["problems_resolved"] == 0
        assert data["average_resolution_days"] is None

    def test_counts_reflect_real_rows(self, api, problem):
        from django.core.cache import cache

        cache.clear()
        data = api.get("/api/v1/stats/public/").json()["data"]
        assert data["problems_reported"] == 1

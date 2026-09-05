"""Experience publishing, support, comments, bookmarks and follows."""

from __future__ import annotations

import pytest

from jandrishti.modules.comments.models import Comment
from jandrishti.modules.experience.models import Experience, ExperienceSupport
from jandrishti.modules.social.models import Bookmark, Follow

pytestmark = pytest.mark.django_db

VALID_EXPERIENCE = {
    "title": "Why resurfacing fails within one monsoon in our ward",
    "experience_type": "ROOT_CAUSE_ANALYSIS",
    "personal_experience": (
        "I spent eleven years supervising road works for a municipal contractor. "
        "In almost every case the failure was not the bitumen but the drainage "
        "beneath it, which nobody inspects before resurfacing begins."
    ),
    "recommendation": (
        "Require a drainage inspection report before any resurfacing tender is "
        "released, and publish that report alongside the work order."
    ),
    "root_cause": "Water ingress under an unsealed base course.",
    "implementation": "Add a mandatory pre-tender drainage checklist.",
    "expected_impact": "Resurfacing should survive several monsoons rather than one.",
    "cost_implications": "Marginal: inspection is a fraction of the resurfacing cost.",
    "state": "Maharashtra",
}


class TestPublishExperience:
    def test_any_signed_in_account_may_contribute(self, auth_client):
        """Eligibility is not gated on verification (spec 3B)."""
        response = auth_client.post("/api/v1/experiences/create/", VALID_EXPERIENCE, format="json")
        assert response.status_code == 201
        assert response.json()["data"]["title"] == VALID_EXPERIENCE["title"]

    def test_thin_submissions_are_refused(self, auth_client):
        response = auth_client.post(
            "/api/v1/experiences/create/",
            {**VALID_EXPERIENCE, "personal_experience": "It is bad."},
            format="json",
        )
        assert response.status_code == 400

    def test_credibility_is_scored_on_publication(self, auth_client):
        response = auth_client.post("/api/v1/experiences/create/", VALID_EXPERIENCE, format="json")
        assert response.json()["data"]["credibility_score"] > 0

    def test_a_detailed_post_outscores_a_bare_one(self, auth_client):
        detailed = auth_client.post(
            "/api/v1/experiences/create/", VALID_EXPERIENCE, format="json"
        ).json()["data"]
        bare = auth_client.post(
            "/api/v1/experiences/create/",
            {
                **VALID_EXPERIENCE,
                "title": "A second contribution with far less structure to it",
                "root_cause": "",
                "implementation": "",
                "expected_impact": "",
                "cost_implications": "",
            },
            format="json",
        ).json()["data"]
        assert detailed["credibility_score"] > bare["credibility_score"]

    def test_verification_status_is_snapshotted_at_publication(self, auth_client, citizen):
        """A later change to the author must not rewrite an old post's provenance."""
        response = auth_client.post("/api/v1/experiences/create/", VALID_EXPERIENCE, format="json")
        experience = Experience.objects.get(public_id=response.json()["data"]["id"])
        assert experience.author_was_verified is False

        citizen.is_professionally_verified = True
        citizen.save(update_fields=["is_professionally_verified"])
        experience.refresh_from_db()
        assert experience.author_was_verified is False

    def test_can_be_linked_to_problems_at_publication(self, auth_client, problem):
        response = auth_client.post(
            "/api/v1/experiences/create/",
            {**VALID_EXPERIENCE, "related_problem_ids": [str(problem.public_id)]},
            format="json",
        )
        assert response.json()["data"]["related_problems"][0]["title"] == problem.title

    def test_related_experiences_appear_on_the_problem(self, auth_client, api, problem):
        auth_client.post(
            "/api/v1/experiences/create/",
            {**VALID_EXPERIENCE, "related_problem_ids": [str(problem.public_id)]},
            format="json",
        )
        response = api.get(f"/api/v1/experiences/for-problem/{problem.public_id}/")
        assert response.status_code == 200
        assert len(response.json()["data"]) == 1


class TestExperienceSupport:
    @pytest.fixture
    def experience(self, auth_client) -> Experience:
        response = auth_client.post("/api/v1/experiences/create/", VALID_EXPERIENCE, format="json")
        return Experience.objects.get(public_id=response.json()["data"]["id"])

    def test_support_counts_once_per_person(self, as_user, other_citizen, experience):
        client = as_user(other_citizen)
        path = f"/api/v1/experiences/{experience.public_id}/support/"
        client.post(path, {}, format="json")
        second = client.post(path, {}, format="json")

        assert second.json()["data"]["already_supported"] is True
        assert ExperienceSupport.objects.filter(experience=experience).count() == 1

    def test_support_is_reversible(self, as_user, other_citizen, experience):
        client = as_user(other_citizen)
        path = f"/api/v1/experiences/{experience.public_id}/support/"
        client.post(path, {}, format="json")
        response = client.delete(path)
        assert response.json()["data"]["support_count"] == 0


class TestComments:
    def test_creates_a_root_comment(self, auth_client, problem):
        response = auth_client.post(
            "/api/v1/comments/",
            {
                "target_type": "PROBLEM",
                "target_id": str(problem.public_id),
                "body": "This has been an issue since last year.",
            },
            format="json",
        )
        assert response.status_code == 201
        assert response.json()["data"]["depth"] == 0

    def test_reply_nests_under_its_parent(self, auth_client, problem):
        parent = auth_client.post(
            "/api/v1/comments/",
            {"target_type": "PROBLEM", "target_id": str(problem.public_id), "body": "Parent"},
            format="json",
        ).json()["data"]

        reply = auth_client.post(
            "/api/v1/comments/",
            {
                "target_type": "PROBLEM",
                "target_id": str(problem.public_id),
                "body": "Reply to the parent",
                "parent_id": parent["id"],
            },
            format="json",
        )
        assert reply.json()["data"]["depth"] == 1

    def test_nesting_is_capped(self, auth_client, problem, settings):
        """Unbounded nesting is a rendering and a moderation problem (spec 25)."""
        settings.COMMENT_MAX_DEPTH = 2
        parent_id = None
        for depth in range(4):
            response = auth_client.post(
                "/api/v1/comments/",
                {
                    "target_type": "PROBLEM",
                    "target_id": str(problem.public_id),
                    "body": f"Comment at depth {depth}",
                    **({"parent_id": parent_id} if parent_id else {}),
                },
                format="json",
            )
            if depth <= 2:
                assert response.status_code == 201, depth
                parent_id = response.json()["data"]["id"]
            else:
                assert response.status_code == 400
                assert "nested" in response.json()["error"]["message"]

    def test_cannot_reply_across_targets(self, auth_client, problem, citizen, category):
        """A parent from another post would let a cycle or a mis-thread form."""
        from jandrishti.modules.problems.models import Problem

        other = Problem.objects.create(
            title="A different problem entirely on another street",
            description="Unrelated to the first problem in every respect whatsoever.",
            reporter=citizen,
            category=category,
            state="Maharashtra",
        )
        parent = auth_client.post(
            "/api/v1/comments/",
            {"target_type": "PROBLEM", "target_id": str(problem.public_id), "body": "Parent"},
            format="json",
        ).json()["data"]

        response = auth_client.post(
            "/api/v1/comments/",
            {
                "target_type": "PROBLEM",
                "target_id": str(other.public_id),
                "body": "Cross-thread reply",
                "parent_id": parent["id"],
            },
            format="json",
        )
        assert response.status_code == 400

    def test_thread_renders_nested(self, auth_client, api, problem):
        parent = auth_client.post(
            "/api/v1/comments/",
            {"target_type": "PROBLEM", "target_id": str(problem.public_id), "body": "Parent"},
            format="json",
        ).json()["data"]
        auth_client.post(
            "/api/v1/comments/",
            {
                "target_type": "PROBLEM",
                "target_id": str(problem.public_id),
                "body": "Child",
                "parent_id": parent["id"],
            },
            format="json",
        )
        data = api.get(f"/api/v1/comments/PROBLEM/{problem.public_id}/").json()["data"]
        assert data["count"] == 2
        assert len(data["comments"]) == 1
        assert data["comments"][0]["replies"][0]["body"] == "Child"

    def test_comment_count_tracks_the_target(self, auth_client, problem):
        auth_client.post(
            "/api/v1/comments/",
            {"target_type": "PROBLEM", "target_id": str(problem.public_id), "body": "One"},
            format="json",
        )
        problem.refresh_from_db()
        assert problem.comment_count == 1

    def test_only_the_author_or_staff_may_delete(
        self, auth_client, as_user, other_citizen, problem
    ):
        comment = auth_client.post(
            "/api/v1/comments/",
            {"target_type": "PROBLEM", "target_id": str(problem.public_id), "body": "Mine"},
            format="json",
        ).json()["data"]

        stranger = as_user(other_citizen)
        assert stranger.delete(f"/api/v1/comments/{comment['id']}/delete/").status_code == 403
        assert auth_client.delete(f"/api/v1/comments/{comment['id']}/delete/").status_code == 200

    def test_deleting_hides_the_comment_but_keeps_replies_addressable(
        self, auth_client, api, problem
    ):
        comment = auth_client.post(
            "/api/v1/comments/",
            {"target_type": "PROBLEM", "target_id": str(problem.public_id), "body": "Mine"},
            format="json",
        ).json()["data"]
        auth_client.delete(f"/api/v1/comments/{comment['id']}/delete/")

        assert (
            api.get(f"/api/v1/comments/PROBLEM/{problem.public_id}/").json()["data"]["count"] == 0
        )
        # Soft delete: the row survives for moderation and audit.
        assert Comment.all_objects.filter(public_id=comment["id"]).exists()


class TestBookmarksAndFollows:
    def test_bookmark_toggles(self, auth_client, problem):
        payload = {"target_type": "PROBLEM", "target_id": str(problem.public_id)}
        assert (
            auth_client.post("/api/v1/social/bookmarks/toggle/", payload, format="json").status_code
            == 201
        )
        assert Bookmark.objects.count() == 1

        auth_client.delete("/api/v1/social/bookmarks/toggle/", payload, format="json")
        assert Bookmark.objects.count() == 0

    def test_bookmarking_twice_does_not_duplicate(self, auth_client, problem):
        payload = {"target_type": "PROBLEM", "target_id": str(problem.public_id)}
        auth_client.post("/api/v1/social/bookmarks/toggle/", payload, format="json")
        auth_client.post("/api/v1/social/bookmarks/toggle/", payload, format="json")
        assert Bookmark.objects.count() == 1

    def test_follow_records_a_readable_title(self, auth_client, problem):
        auth_client.post(
            "/api/v1/social/follows/toggle/",
            {"target_type": "PROBLEM", "target_id": str(problem.public_id)},
            format="json",
        )
        assert Follow.objects.get().target_title == problem.title

    def test_bookmark_list_is_scoped_to_the_owner(
        self, auth_client, as_user, other_citizen, problem
    ):
        auth_client.post(
            "/api/v1/social/bookmarks/toggle/",
            {"target_type": "PROBLEM", "target_id": str(problem.public_id)},
            format="json",
        )
        assert len(as_user(other_citizen).get("/api/v1/social/bookmarks/").json()["data"]) == 0
        assert len(auth_client.get("/api/v1/social/bookmarks/").json()["data"]) == 1

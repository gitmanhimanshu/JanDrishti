"""
Security tests (spec 69).

IDOR, privilege escalation, upload abuse, and the privacy rules around
verification documents and Aadhaar. These are the tests worth failing loudly.
"""

from __future__ import annotations

import json

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile

from jandrishti.modules.accounts.domain.enums import ProfessionalCategory, UserRole
from jandrishti.modules.media.application.service import MediaService, UploadRequest
from jandrishti.modules.professional_verification.models import (
    ProfessionalVerification,
    VerificationStatus,
)
from jandrishti.shared.domain.exceptions import ValidationError
from jandrishti.shared.infrastructure.logging import scrub

pytestmark = pytest.mark.django_db


class TestPrivilegeEscalation:
    def test_user_cannot_promote_themselves_to_admin(self, auth_client, citizen):
        response = auth_client.post(
            "/api/v1/users/me/user-type/", {"role": UserRole.ADMIN}, format="json"
        )
        assert response.status_code == 400
        citizen.refresh_from_db()
        assert citizen.role == UserRole.CITIZEN

    def test_user_cannot_promote_themselves_to_government_official(self, auth_client, citizen):
        response = auth_client.post(
            "/api/v1/users/me/user-type/",
            {"role": UserRole.GOVERNMENT_OFFICIAL},
            format="json",
        )
        assert response.status_code == 400
        citizen.refresh_from_db()
        assert citizen.role == UserRole.CITIZEN

    def test_patching_the_profile_cannot_change_the_role(self, auth_client, citizen):
        auth_client.patch(
            "/api/v1/users/me/",
            {"role": UserRole.ADMIN, "is_professionally_verified": True, "full_name": "Real Name"},
            format="json",
        )
        citizen.refresh_from_db()
        assert citizen.role == UserRole.CITIZEN
        assert citizen.is_professionally_verified is False
        assert citizen.full_name == "Real Name"

    def test_selecting_professional_grants_no_badge(self, auth_client, citizen):
        """Declaring a role is not evidence of one (spec 6, 28)."""
        auth_client.post(
            "/api/v1/users/me/user-type/",
            {"role": UserRole.PROFESSIONAL, "professional_category": "DOMAIN_EXPERT"},
            format="json",
        )
        citizen.refresh_from_db()
        assert citizen.role == UserRole.PROFESSIONAL
        assert citizen.is_professionally_verified is False
        assert citizen.verified_category == ""

    def test_role_in_the_token_does_not_grant_access(self, api, citizen):
        """The server reads the role from the database, never from the token."""
        from jandrishti.modules.authentication.infrastructure.tokens import JWTTokenService

        forged, _ = JWTTokenService().issue_access_token(str(citizen.id), "ADMIN")
        api.credentials(HTTP_AUTHORIZATION=f"Bearer {forged}")
        assert api.get("/api/v1/audit/").status_code == 403

    def test_citizen_cannot_reach_the_moderation_queue(self, auth_client):
        assert auth_client.get("/api/v1/moderation/queue/").status_code == 403

    def test_citizen_cannot_reach_the_verification_queue(self, auth_client):
        assert auth_client.get("/api/v1/verification/queue/").status_code == 403

    def test_citizen_cannot_create_a_project(self, auth_client):
        assert auth_client.post("/api/v1/projects/create/", {}, format="json").status_code == 403


class TestTokenHandling:
    def test_garbage_token_is_rejected(self, api):
        api.credentials(HTTP_AUTHORIZATION="Bearer not-a-real-token")
        assert api.get("/api/v1/users/me/").status_code == 401

    def test_token_signed_with_another_key_is_rejected(self, api, citizen):
        from jandrishti.modules.authentication.infrastructure.tokens import JWTTokenService

        attacker_token, _ = JWTTokenService(secret="a-different-secret").issue_access_token(
            str(citizen.id), "ADMIN"
        )
        api.credentials(HTTP_AUTHORIZATION=f"Bearer {attacker_token}")
        assert api.get("/api/v1/users/me/").status_code == 401

    def test_banned_account_loses_access(self, api, citizen):
        from jandrishti.modules.authentication.infrastructure.tokens import JWTTokenService

        citizen.is_banned = True
        citizen.save(update_fields=["is_banned"])
        token, _ = JWTTokenService().issue_access_token(str(citizen.id), citizen.role)
        api.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
        assert api.get("/api/v1/users/me/").status_code == 401

    def test_no_credentials_still_serves_public_content(self, api, problem):
        assert api.get("/api/v1/problems/").status_code == 200


class TestIDOR:
    def test_notifications_are_scoped_to_the_recipient(self, as_user, citizen, other_citizen):
        from jandrishti.modules.notifications.models import Notification, NotificationKind

        Notification.objects.create(
            recipient=citizen,
            kind=NotificationKind.PROBLEM_STATUS_CHANGED,
            title="Private to the first user",
        )
        data = as_user(other_citizen).get("/api/v1/notifications/").json()["data"]
        assert data == []

    def test_cannot_attach_another_users_media(self, citizen, other_citizen, problem):
        """Ownership is re-checked at attach time, not just at upload."""
        media = MediaService().upload(
            UploadRequest(
                file=SimpleUploadedFile("a.png", _png_bytes(), content_type="image/png"),
                uploaded_by=other_citizen,
            )
        )
        with pytest.raises(ValidationError):
            MediaService().attach(
                [str(media.public_id)],
                target_type="PROBLEM",
                target_id=problem.id,
                owner=citizen,
            )

    def test_public_profile_does_not_leak_the_email(self, api, citizen):
        body = api.get(f"/api/v1/users/{citizen.id}/").content.decode()
        assert citizen.email not in body
        assert "email" not in api.get(f"/api/v1/users/{citizen.id}/").json()["data"]

    def test_self_view_does_show_own_email(self, auth_client, citizen):
        assert auth_client.get("/api/v1/users/me/").json()["data"]["email"] == citizen.email


def _png_bytes() -> bytes:
    """A minimal but genuinely PNG-signed byte string."""
    return b"\x89PNG\r\n\x1a\n" + b"\x00" * 64


class TestUploadValidation:
    def test_rejects_a_disallowed_type(self, citizen):
        with pytest.raises(ValidationError):
            MediaService().validate(
                SimpleUploadedFile("x.exe", b"MZ\x00\x00", content_type="application/x-msdownload")
            )

    def test_rejects_content_that_contradicts_its_declared_type(self, citizen):
        """A script renamed to .jpg must not pass because the header says JPEG."""
        with pytest.raises(ValidationError) as exc:
            MediaService().validate(
                SimpleUploadedFile(
                    "evil.jpg", b"<?php system($_GET[0]); ?>", content_type="image/jpeg"
                )
            )
        assert "do not match" in exc.value.message

    def test_rejects_an_oversized_file(self, citizen):
        from django.conf import settings as django_settings

        oversized = SimpleUploadedFile("big.png", _png_bytes(), content_type="image/png")
        # Set the reported size past the limit without allocating that many
        # bytes -- the size check must not depend on reading the whole upload.
        oversized.size = django_settings.MAX_UPLOAD_SIZE_IMAGE + 1

        with pytest.raises(ValidationError) as exc:
            MediaService().validate(oversized)
        assert "too large" in exc.value.message

    def test_accepts_a_well_formed_image(self, citizen):
        assert (
            MediaService().validate(
                SimpleUploadedFile("ok.png", _png_bytes(), content_type="image/png")
            )
            == "IMAGE"
        )


class TestVerificationPrivacy:
    def test_aadhaar_number_is_not_a_field_anywhere_on_the_model(self):
        """The number must not be storable, not merely un-stored."""
        field_names = {field.name for field in ProfessionalVerification._meta.get_fields()}
        assert "aadhaar_number" not in field_names
        assert "aadhaar" not in field_names
        assert {"aadhaar_reference", "aadhaar_last4"} <= field_names

    def test_submitting_an_aadhaar_number_is_ignored_not_stored(self, auth_client):
        response = auth_client.post(
            "/api/v1/verification/submit/",
            {
                "claimed_category": ProfessionalCategory.RETIRED_GOVERNMENT_EMPLOYEE,
                "method": "AADHAAR_FALLBACK",
                "aadhaar_reference": "provider-txn-abc123",
                "aadhaar_last4": "6789",
                "aadhaar_number": "1234 5678 6789",
            },
            format="json",
        )
        assert response.status_code == 201
        verification = ProfessionalVerification.objects.get()
        assert not hasattr(verification, "aadhaar_number")
        assert verification.aadhaar_last4 == "6789"
        assert "1234" not in json.dumps(response.json())

    def test_documents_must_be_uploaded_privately(self, auth_client, citizen):
        public_media = MediaService().upload(
            UploadRequest(
                file=SimpleUploadedFile("doc.png", _png_bytes(), content_type="image/png"),
                uploaded_by=citizen,
                private=False,
            )
        )
        response = auth_client.post(
            "/api/v1/verification/submit/",
            {
                "claimed_category": ProfessionalCategory.DOMAIN_EXPERT,
                "documents": [{"media_id": str(public_media.public_id)}],
            },
            format="json",
        )
        assert response.status_code == 400
        assert "private" in response.json()["error"]["message"]

    def test_private_upload_returns_no_url(self, auth_client):
        response = auth_client.post(
            "/api/v1/verification/documents/upload/",
            {"file": SimpleUploadedFile("id.png", _png_bytes(), content_type="image/png")},
            format="multipart",
        )
        assert response.status_code == 201
        body = json.dumps(response.json())
        assert "url" not in response.json()["data"]
        assert "http" not in body

    def test_document_evidence_is_required(self, auth_client):
        response = auth_client.post(
            "/api/v1/verification/submit/",
            {"claimed_category": ProfessionalCategory.DOMAIN_EXPERT},
            format="json",
        )
        assert response.status_code == 400

    def test_only_a_moderator_can_open_a_document(self, auth_client):
        response = auth_client.get(
            "/api/v1/verification/documents/00000000-0000-0000-0000-000000000000/access/"
        )
        assert response.status_code == 403


class TestVerificationReview:
    @pytest.fixture
    def pending(self, auth_client, citizen) -> ProfessionalVerification:
        auth_client.post(
            "/api/v1/verification/submit/",
            {
                "claimed_category": ProfessionalCategory.RETIRED_GOVERNMENT_EMPLOYEE,
                "method": "AADHAAR_FALLBACK",
                "aadhaar_reference": "provider-txn-abc123",
                "aadhaar_last4": "6789",
            },
            format="json",
        )
        return ProfessionalVerification.objects.get()

    def test_approval_grants_the_badge(self, pending, as_user, moderator, citizen):
        response = as_user(moderator).post(
            f"/api/v1/verification/{pending.public_id}/review/",
            {"decision": VerificationStatus.VERIFIED},
            format="json",
        )
        assert response.status_code == 200
        citizen.refresh_from_db()
        assert citizen.is_professionally_verified is True
        assert citizen.verified_category == ProfessionalCategory.RETIRED_GOVERNMENT_EMPLOYEE

    def test_rejection_grants_nothing(self, pending, as_user, moderator, citizen):
        as_user(moderator).post(
            f"/api/v1/verification/{pending.public_id}/review/",
            {"decision": VerificationStatus.REJECTED, "rejection_reason": "Document unreadable."},
            format="json",
        )
        citizen.refresh_from_db()
        assert citizen.is_professionally_verified is False

    def test_a_decision_cannot_be_made_twice(self, pending, as_user, moderator):
        client = as_user(moderator)
        path = f"/api/v1/verification/{pending.public_id}/review/"
        client.post(path, {"decision": VerificationStatus.VERIFIED}, format="json")
        second = client.post(path, {"decision": VerificationStatus.REJECTED}, format="json")
        assert second.status_code == 409

    def test_nobody_reviews_their_own_request(self, as_user, moderator):
        """A moderator with a pending claim must not be able to approve it."""
        client = as_user(moderator)
        client.post(
            "/api/v1/verification/submit/",
            {
                "claimed_category": ProfessionalCategory.DOMAIN_EXPERT,
                "method": "AADHAAR_FALLBACK",
                "aadhaar_reference": "self-txn",
                "aadhaar_last4": "1111",
            },
            format="json",
        )
        own = ProfessionalVerification.objects.get(user=moderator)
        response = client.post(
            f"/api/v1/verification/{own.public_id}/review/",
            {"decision": VerificationStatus.VERIFIED},
            format="json",
        )
        assert response.status_code == 403

    def test_the_decision_is_audited(self, pending, as_user, moderator):
        from jandrishti.modules.audit.models import AuditLog

        as_user(moderator).post(
            f"/api/v1/verification/{pending.public_id}/review/",
            {"decision": VerificationStatus.VERIFIED},
            format="json",
        )
        assert AuditLog.objects.filter(action="verification.decided").exists()


class TestLogRedaction:
    def test_aadhaar_shaped_strings_are_scrubbed(self):
        assert "1234" not in scrub("user submitted 1234 5678 9012 today")

    def test_bearer_tokens_are_scrubbed(self):
        assert "abc.def.ghi" not in scrub("Authorization: Bearer abc.def.ghi")

    def test_sensitive_keys_are_scrubbed(self):
        cleaned = scrub({"refresh_token": "secret-value", "title": "a public title"})
        assert cleaned["refresh_token"] == "[REDACTED]"
        assert cleaned["title"] == "a public title"

    def test_nested_structures_are_scrubbed(self):
        cleaned = scrub({"outer": [{"client_secret": "abc"}]})
        assert cleaned["outer"][0]["client_secret"] == "[REDACTED]"


class TestFundingIsOff:
    def test_contributing_returns_an_honest_refusal(self, auth_client, citizen, problem):
        from jandrishti.modules.funding.models import FundingCampaign
        from jandrishti.modules.projects.models import Project

        project = Project.objects.create(title="Road repair", description="x" * 40)
        campaign = FundingCampaign.objects.create(
            project=project, title="Repair fund", description="x" * 40, target_amount=100000
        )
        response = auth_client.post(
            f"/api/v1/funding/campaigns/{campaign.public_id}/contribute/",
            {"amount": "500"},
            format="json",
        )
        assert response.status_code == 503
        assert response.json()["error"]["code"] == "FEATURE_DISABLED"

    def test_the_default_gateway_refuses_to_charge(self):
        from decimal import Decimal

        from jandrishti.modules.funding.domain.gateway import get_payment_gateway
        from jandrishti.shared.domain.exceptions import FeatureDisabledError

        with pytest.raises(FeatureDisabledError):
            get_payment_gateway().create_intent(
                amount=Decimal("100"), currency="INR", idempotency_key="k", metadata={}
            )

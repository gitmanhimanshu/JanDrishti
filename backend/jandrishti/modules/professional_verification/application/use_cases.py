"""
Verification use cases: submit, review, purge.

The badge on a profile is set in exactly one place -- `ReviewVerificationUseCase`
-- and only as the result of a human decision. Nothing automated can grant it.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

from django.conf import settings
from django.utils import timezone

from jandrishti.modules.accounts.domain.enums import ProfessionalCategory, UserRole
from jandrishti.modules.audit.application.recorder import record_audit
from jandrishti.modules.media.models import Media
from jandrishti.shared.application.use_case import Actor, UseCase
from jandrishti.shared.domain.events import Events, make_event
from jandrishti.shared.domain.exceptions import (
    ConflictError,
    NotFoundError,
    PermissionDeniedError,
    ValidationError,
)

from ..models import (
    ProfessionalVerification,
    VerificationDocument,
    VerificationMethod,
    VerificationStatus,
)

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class SubmitVerificationCommand:
    claimed_category: str
    method: str = VerificationMethod.DOCUMENT
    organization: str = ""
    designation: str = ""
    employee_reference: str = ""
    service_start_year: int | None = None
    service_end_year: int | None = None
    applicant_note: str = ""
    documents: list[dict] = field(default_factory=list)
    aadhaar_reference: str = ""
    aadhaar_last4: str = ""
    aadhaar_provider: str = ""
    actor: Actor = field(default_factory=Actor.anonymous)


class SubmitVerificationUseCase(UseCase[SubmitVerificationCommand, ProfessionalVerification]):
    def handle(self, request: SubmitVerificationCommand) -> ProfessionalVerification:
        user = request.actor.require_authenticated()
        if not user.can_interact:
            raise PermissionDeniedError("This account cannot submit a verification request.")

        if request.claimed_category not in ProfessionalCategory.values:
            raise ValidationError("Unknown professional category.")

        open_request = ProfessionalVerification.objects.filter(
            user=user,
            status__in=[VerificationStatus.PENDING, VerificationStatus.MORE_INFO_REQUIRED],
        ).first()
        if open_request and open_request.status == VerificationStatus.PENDING:
            raise ConflictError("You already have a verification request under review.")

        self._assert_evidence_present(request)

        verification = open_request or ProfessionalVerification(user=user)
        verification.claimed_category = request.claimed_category
        verification.method = (
            request.method
            if request.method in VerificationMethod.values
            else VerificationMethod.DOCUMENT
        )
        verification.organization = request.organization[:200]
        verification.designation = request.designation[:150]
        verification.employee_reference = request.employee_reference[:100]
        verification.service_start_year = request.service_start_year
        verification.service_end_year = request.service_end_year
        verification.applicant_note = request.applicant_note[:2000]
        verification.status = VerificationStatus.PENDING

        if request.method == VerificationMethod.AADHAAR_FALLBACK:
            # Only the provider reference and the last four digits. The number
            # itself never enters this process.
            verification.aadhaar_reference = request.aadhaar_reference[:128]
            verification.aadhaar_last4 = request.aadhaar_last4[-4:]
            verification.aadhaar_provider = request.aadhaar_provider[:60]
            verification.aadhaar_verified_at = timezone.now()

        verification.save()
        self._attach_documents(verification, request.documents, user)

        record_audit(
            action="verification.submitted",
            actor=user,
            target=f"verification:{verification.public_id}",
            metadata={
                "category": request.claimed_category,
                "method": verification.method,
                "document_count": len(request.documents),
            },
            ip_address=request.actor.ip_address or None,
        )
        self.record(
            make_event(
                Events.VERIFICATION_SUBMITTED,
                verification_id=str(verification.public_id),
                user_id=str(user.id),
            )
        )
        return verification

    @staticmethod
    def _assert_evidence_present(request: SubmitVerificationCommand) -> None:
        if request.method == VerificationMethod.AADHAAR_FALLBACK:
            if not request.aadhaar_reference:
                raise ValidationError(
                    "Complete the identity check with the provider before submitting."
                )
            return
        if not request.documents:
            raise ValidationError("Attach at least one supporting document.")

    @staticmethod
    def _attach_documents(
        verification: ProfessionalVerification, documents: list[dict], user
    ) -> None:
        media_ids = [doc.get("media_id") for doc in documents if doc.get("media_id")]
        if not media_ids:
            return
        # Ownership check plus the privacy flag: a verification document must
        # have been uploaded privately, and by this applicant.
        media_map = {
            str(media.public_id): media
            for media in Media.objects.filter(
                public_id__in=media_ids[:10], uploaded_by=user, is_private=True
            )
        }
        if len(media_map) != len(set(media_ids[:10])):
            raise ValidationError(
                "Verification documents must be uploaded through the private upload endpoint."
            )
        VerificationDocument.objects.bulk_create(
            [
                VerificationDocument(
                    verification=verification,
                    kind=doc.get("kind", VerificationDocument.Kind.OTHER),
                    media=media_map[str(doc["media_id"])],
                    note=str(doc.get("note", ""))[:300],
                )
                for doc in documents[:10]
            ]
        )


@dataclass(slots=True)
class ReviewVerificationCommand:
    verification_id: str
    decision: str
    reviewer_note: str = ""
    rejection_reason: str = ""
    actor: Actor = field(default_factory=Actor.anonymous)


class ReviewVerificationUseCase(UseCase[ReviewVerificationCommand, ProfessionalVerification]):
    """The human decision, and the only writer of the verification badge."""

    ALLOWED_DECISIONS = {
        VerificationStatus.VERIFIED,
        VerificationStatus.REJECTED,
        VerificationStatus.MORE_INFO_REQUIRED,
    }

    def handle(self, request: ReviewVerificationCommand) -> ProfessionalVerification:
        reviewer = request.actor.require_role(UserRole.MODERATOR, UserRole.ADMIN)
        if request.decision not in self.ALLOWED_DECISIONS:
            raise ValidationError("Unknown verification decision.")

        verification = (
            ProfessionalVerification.objects.select_for_update()
            .select_related("user")
            .filter(public_id=request.verification_id)
            .first()
        )
        if verification is None:
            raise NotFoundError("Verification request not found.")
        if verification.is_decided:
            raise ConflictError("This request has already been decided.")
        if verification.user_id == reviewer.id:
            raise PermissionDeniedError("You cannot review your own verification request.")

        verification.status = request.decision
        verification.reviewed_by = reviewer
        verification.reviewed_at = timezone.now()
        verification.reviewer_note = request.reviewer_note[:2000]
        verification.rejection_reason = request.rejection_reason[:500]
        verification.save()

        user = verification.user
        if request.decision == VerificationStatus.VERIFIED:
            user.is_professionally_verified = True
            user.verified_category = verification.claimed_category
            user.verified_at = verification.reviewed_at
            if user.role == UserRole.CITIZEN:
                user.role = UserRole.PROFESSIONAL
            user.save(
                update_fields=[
                    "is_professionally_verified",
                    "verified_category",
                    "verified_at",
                    "role",
                    "updated_at",
                ]
            )

        record_audit(
            action="verification.decided",
            actor=reviewer,
            target=f"verification:{verification.public_id}",
            metadata={
                "subject_user": str(user.id),
                "decision": request.decision,
                "category": verification.claimed_category,
            },
            ip_address=request.actor.ip_address or None,
        )
        self.record(
            make_event(
                Events.VERIFICATION_COMPLETED,
                verification_id=str(verification.public_id),
                user_id=str(user.id),
                decision=request.decision,
            )
        )
        return verification


def purge_expired_documents() -> int:
    """Delete verification documents past their retention window.

    Privacy by design is a schedule, not an intention: keeping a scan of
    somebody's service record forever because nobody wrote the deletion job is
    the failure mode this exists to prevent (spec 68).
    """
    from jandrishti.modules.media.infrastructure.storage import get_media_storage

    cutoff = timezone.now() - timezone.timedelta(days=settings.VERIFICATION_DOCUMENT_RETENTION_DAYS)
    storage = get_media_storage()
    purged = 0

    documents = VerificationDocument.objects.filter(
        purged_at__isnull=True,
        verification__reviewed_at__lt=cutoff,
        verification__status__in=[VerificationStatus.VERIFIED, VerificationStatus.REJECTED],
    ).select_related("media", "verification")

    for document in documents.iterator(chunk_size=100):
        try:
            storage.delete(document.media.storage_key, resource_type="raw")
        except Exception:
            logger.exception("failed to delete verification document from storage")
            continue
        now = timezone.now()
        document.purged_at = now
        document.save(update_fields=["purged_at", "updated_at"])
        # The media row keeps its metadata for audit, but no longer points at
        # anything readable.
        Media.objects.filter(pk=document.media_id).update(url="", thumbnail_url="")
        ProfessionalVerification.objects.filter(pk=document.verification_id).update(
            documents_purged_at=now
        )
        purged += 1

    if purged:
        record_audit(
            action="verification.documents_purged",
            target="verification:retention",
            metadata={
                "count": purged,
                "retention_days": settings.VERIFICATION_DOCUMENT_RETENTION_DAYS,
            },
        )
    return purged

"""
Professional verification (spec 28, 29, 30).

Authentication and verification are separate systems. Signing in with Google
proves control of a Google account; it says nothing about a profession. This
module is where a claim becomes evidence-backed, reviewed by a human, and only
then reflected as a badge.

Aadhaar handling, which is the sensitive part:

* it is never mandatory, never a login credential, and never the primary key;
* the number itself is not stored -- only the provider's reference token and
  the last four digits, which are what a reviewer needs to talk to the user;
* it never appears in a URL, a public serializer, a log line or an API response;
* documents live in private storage and are purged on a retention schedule.
"""

from __future__ import annotations

from datetime import timedelta

from django.conf import settings
from django.db import models
from django.utils import timezone

from jandrishti.modules.accounts.domain.enums import ProfessionalCategory
from jandrishti.shared.models import BaseEntity


class VerificationStatus(models.TextChoices):
    DRAFT = "DRAFT", "Draft"
    PENDING = "PENDING", "Pending review"
    MORE_INFO_REQUIRED = "MORE_INFO_REQUIRED", "More information required"
    VERIFIED = "VERIFIED", "Verified"
    REJECTED = "REJECTED", "Rejected"
    EXPIRED = "EXPIRED", "Expired"


class VerificationMethod(models.TextChoices):
    DOCUMENT = "DOCUMENT", "Professional document"
    ORGANIZATION_EMAIL = "ORGANIZATION_EMAIL", "Organization email"
    # Fallback only, for people with no suitable professional document.
    AADHAAR_FALLBACK = "AADHAAR_FALLBACK", "Aadhaar-based identity fallback"
    MANUAL_REVIEW = "MANUAL_REVIEW", "Manual review"


class ProfessionalVerification(BaseEntity):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="verifications"
    )
    claimed_category = models.CharField(max_length=40, choices=ProfessionalCategory.choices)
    method = models.CharField(
        max_length=30, choices=VerificationMethod.choices, default=VerificationMethod.DOCUMENT
    )
    status = models.CharField(
        max_length=25,
        choices=VerificationStatus.choices,
        default=VerificationStatus.PENDING,
        db_index=True,
    )

    organization = models.CharField(max_length=200, blank=True)
    designation = models.CharField(max_length=150, blank=True)
    employee_reference = models.CharField(max_length=100, blank=True)
    service_start_year = models.PositiveSmallIntegerField(null=True, blank=True)
    service_end_year = models.PositiveSmallIntegerField(null=True, blank=True)
    applicant_note = models.TextField(max_length=2000, blank=True)

    # -- Aadhaar fallback ----------------------------------------------------
    # The number is NOT here, and must never be added. The provider returns an
    # opaque reference for an eKYC transaction; that is all we keep, alongside
    # the last four digits so a reviewer can confirm with the applicant.
    aadhaar_reference = models.CharField(max_length=128, blank=True)
    aadhaar_last4 = models.CharField(max_length=4, blank=True)
    aadhaar_verified_at = models.DateTimeField(null=True, blank=True)
    aadhaar_provider = models.CharField(max_length=60, blank=True)

    # -- review --------------------------------------------------------------
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="verification_reviews",
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    reviewer_note = models.TextField(max_length=2000, blank=True)
    rejection_reason = models.CharField(max_length=500, blank=True)
    expires_at = models.DateTimeField(null=True, blank=True)

    # Set once the private documents behind this request have been purged.
    documents_purged_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "professional_verification"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["status", "-created_at"]),
            models.Index(fields=["user", "-created_at"]),
        ]
        constraints = [
            # One open request per person: resubmitting should update the
            # existing request, not stack a queue of duplicates on reviewers.
            models.UniqueConstraint(
                fields=["user"],
                condition=models.Q(status__in=["PENDING", "MORE_INFO_REQUIRED"]),
                name="uq_one_open_verification_per_user",
            )
        ]

    def __str__(self) -> str:
        return f"{self.user} — {self.get_claimed_category_display()} ({self.status})"

    @property
    def is_decided(self) -> bool:
        return self.status in {VerificationStatus.VERIFIED, VerificationStatus.REJECTED}

    @property
    def retention_due_at(self):
        """When the supporting documents must be deleted (spec 29, 68)."""
        if not self.reviewed_at:
            return None
        return self.reviewed_at + timedelta(days=settings.VERIFICATION_DOCUMENT_RETENTION_DAYS)


class VerificationDocument(BaseEntity):
    """A private document supporting a claim.

    Points at a Media row uploaded with `is_private=True`, so it is never
    reachable through a public URL. Every read goes through an authorized
    endpoint that writes an audit record first.
    """

    class Kind(models.TextChoices):
        ORGANIZATION_ID = "ORGANIZATION_ID", "Organization-issued identity"
        EMPLOYMENT_LETTER = "EMPLOYMENT_LETTER", "Employment or service letter"
        RETIREMENT_ORDER = "RETIREMENT_ORDER", "Retirement or service order"
        PROFESSIONAL_LICENSE = "PROFESSIONAL_LICENSE", "Professional licence or certificate"
        GOVERNMENT_DOCUMENT = "GOVERNMENT_DOCUMENT", "Government-issued professional document"
        OTHER = "OTHER", "Other supporting document"

    verification = models.ForeignKey(
        ProfessionalVerification, on_delete=models.CASCADE, related_name="documents"
    )
    kind = models.CharField(max_length=40, choices=Kind.choices, default=Kind.OTHER)
    media = models.ForeignKey("media.Media", on_delete=models.CASCADE, related_name="+")
    note = models.CharField(max_length=300, blank=True)
    purged_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "professional_verification_document"

    def __str__(self) -> str:
        return f"{self.get_kind_display()} for {self.verification_id}"


class DocumentAccessLog(models.Model):
    """Every look at a private verification document is recorded.

    Section 63 lists sensitive-document access as auditable. A reviewer opening
    somebody's service record is exactly that.
    """

    document = models.ForeignKey(
        VerificationDocument, on_delete=models.CASCADE, related_name="access_logs"
    )
    accessed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="+"
    )
    accessed_at = models.DateTimeField(default=timezone.now, db_index=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    reason = models.CharField(max_length=200, blank=True)

    class Meta:
        db_table = "professional_verification_document_access"
        indexes = [models.Index(fields=["document", "-accessed_at"])]

    def __str__(self) -> str:
        return f"document {self.document_id} read by {self.accessed_by_id}"

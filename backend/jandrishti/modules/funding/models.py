"""
Community funding (spec 36).

Read this before enabling anything here.

Real money is OFF by default and stays off until the legal and payment
architecture in docs/decisions/funding.md exists: a regulated payment provider,
a legal entity to receive funds, escrow where applicable, KYC/AML, a refund and
dispute process, and financial auditability. Community money must never route
into a personal bank account.

What this module provides today is the *schema and the interfaces*, so the
financial transparency model is designed in from the start rather than bolted
on. The gateway adapter is a null implementation that refuses to charge anyone.
"""

from __future__ import annotations

from django.conf import settings
from django.db import models

from jandrishti.shared.models import BaseEntity


class CampaignStatus(models.TextChoices):
    DRAFT = "DRAFT", "Draft"
    # Nothing may move to ACTIVE while FUNDING_PAYMENTS_ENABLED is false.
    PENDING_APPROVAL = "PENDING_APPROVAL", "Pending approval"
    ACTIVE = "ACTIVE", "Active"
    PAUSED = "PAUSED", "Paused"
    SUCCESSFUL = "SUCCESSFUL", "Successful"
    CLOSED = "CLOSED", "Closed"
    CANCELLED = "CANCELLED", "Cancelled"


class FundingCampaign(BaseEntity):
    project = models.ForeignKey(
        "projects.Project", on_delete=models.CASCADE, related_name="campaigns"
    )
    title = models.CharField(max_length=200)
    description = models.TextField(max_length=6000)
    status = models.CharField(
        max_length=20, choices=CampaignStatus.choices, default=CampaignStatus.DRAFT, db_index=True
    )

    target_amount = models.DecimalField(max_digits=14, decimal_places=2)
    collected_amount = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    spent_amount = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    contributor_count = models.PositiveIntegerField(default=0)

    starts_at = models.DateTimeField(null=True, blank=True)
    ends_at = models.DateTimeField(null=True, blank=True)

    # The legal entity that will actually hold the money. A campaign cannot go
    # live without one, which is the schema-level expression of the rule that
    # community funds never sit in a personal account.
    legal_entity_name = models.CharField(max_length=200, blank=True)
    legal_entity_registration = models.CharField(max_length=100, blank=True)
    escrow_reference = models.CharField(max_length=120, blank=True)

    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )
    approved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "funding_campaign"
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["status", "-created_at"])]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(target_amount__gt=0), name="ck_campaign_target_positive"
            ),
            models.CheckConstraint(
                condition=models.Q(collected_amount__gte=0) & models.Q(spent_amount__gte=0),
                name="ck_campaign_amounts_non_negative",
            ),
        ]

    def __str__(self) -> str:
        return self.title

    @property
    def remaining_amount(self):
        return self.collected_amount - self.spent_amount

    @property
    def public_summary(self) -> dict:
        """The four numbers the public is owed: target, collected, spent, remaining."""
        return {
            "target": str(self.target_amount),
            "collected": str(self.collected_amount),
            "spent": str(self.spent_amount),
            "remaining": str(self.remaining_amount),
            "contributor_count": self.contributor_count,
        }


class Contribution(BaseEntity):
    class Status(models.TextChoices):
        INITIATED = "INITIATED", "Initiated"
        SUCCEEDED = "SUCCEEDED", "Succeeded"
        FAILED = "FAILED", "Failed"
        REFUNDED = "REFUNDED", "Refunded"

    campaign = models.ForeignKey(
        FundingCampaign, on_delete=models.CASCADE, related_name="contributions"
    )
    contributor = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="contributions"
    )
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.INITIATED)
    is_anonymous = models.BooleanField(default=False)
    message = models.CharField(max_length=300, blank=True)

    # Provider-side identifiers only. No card, bank or UPI detail is ever
    # stored here -- that is the payment provider's job and their compliance
    # burden, not ours.
    provider = models.CharField(max_length=40, blank=True)
    provider_reference = models.CharField(max_length=120, blank=True, db_index=True)
    # Idempotency key: a retried callback must not create a second payment.
    idempotency_key = models.CharField(max_length=80, unique=True)
    settled_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "funding_contribution"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["campaign", "status"]),
            models.Index(fields=["contributor", "-created_at"]),
        ]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(amount__gt=0), name="ck_contribution_amount_positive"
            )
        ]


class Expense(BaseEntity):
    """Where the money went. Public, itemised and evidence-backed."""

    class Status(models.TextChoices):
        RECORDED = "RECORDED", "Recorded"
        UNDER_VERIFICATION = "UNDER_VERIFICATION", "Under verification"
        VERIFIED = "VERIFIED", "Verified"
        DISPUTED = "DISPUTED", "Disputed"

    campaign = models.ForeignKey(FundingCampaign, on_delete=models.CASCADE, related_name="expenses")
    project = models.ForeignKey(
        "projects.Project", on_delete=models.CASCADE, related_name="expenses"
    )
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    vendor = models.CharField(max_length=200)
    description = models.TextField(max_length=2000)
    incurred_on = models.DateField()
    invoice_number = models.CharField(max_length=100, blank=True)
    status = models.CharField(max_length=25, choices=Status.choices, default=Status.RECORDED)

    recorded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="+"
    )
    verified_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )
    verified_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "funding_expense"
        ordering = ["-incurred_on"]
        indexes = [models.Index(fields=["campaign", "-incurred_on"])]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(amount__gt=0), name="ck_expense_amount_positive"
            )
        ]

    def __str__(self) -> str:
        return f"{self.vendor}: {self.amount}"

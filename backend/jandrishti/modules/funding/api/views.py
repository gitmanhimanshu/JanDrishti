"""
Funding endpoints.

Reads are public -- financial transparency is the reason this module exists.
Contribution is gated behind the payment gateway, which refuses while payments
are disabled, so the API returns an honest 503 rather than a fake success.
"""

from __future__ import annotations

from django.conf import settings
from rest_framework import serializers
from rest_framework.generics import ListAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from jandrishti.shared.api.pagination import StandardPageNumberPagination
from jandrishti.shared.api.response import error, ok
from jandrishti.shared.api.views import ActorMixin

from ..domain.gateway import get_payment_gateway
from ..models import Contribution, Expense, FundingCampaign


class CampaignSerializer(serializers.ModelSerializer):
    id = serializers.UUIDField(source="public_id", read_only=True)
    project_id = serializers.UUIDField(source="project.public_id", read_only=True)
    summary = serializers.SerializerMethodField()

    class Meta:
        model = FundingCampaign
        fields = [
            "id",
            "project_id",
            "title",
            "description",
            "status",
            "summary",
            "legal_entity_name",
            "starts_at",
            "ends_at",
            "created_at",
        ]

    def get_summary(self, obj: FundingCampaign) -> dict:
        return obj.public_summary


class ExpenseSerializer(serializers.ModelSerializer):
    id = serializers.UUIDField(source="public_id", read_only=True)
    evidence = serializers.SerializerMethodField()

    class Meta:
        model = Expense
        fields = [
            "id",
            "amount",
            "vendor",
            "description",
            "incurred_on",
            "invoice_number",
            "status",
            "verified_at",
            "evidence",
        ]

    def get_evidence(self, obj: Expense) -> list[dict]:
        from jandrishti.modules.media.api.views import MediaSerializer

        media_map = self.context.get("expense_media_map") or {}
        return MediaSerializer(media_map.get(obj.id, []), many=True).data


class CampaignListView(ListAPIView):
    serializer_class = CampaignSerializer
    pagination_class = StandardPageNumberPagination
    filterset_fields = ["status"]
    queryset = FundingCampaign.objects.select_related("project").order_by("-created_at")


class CampaignDetailView(APIView):
    """Campaign plus its itemised expenses -- the accountability view."""

    def get(self, request: Request, campaign_id: str) -> Response:
        campaign = (
            FundingCampaign.objects.select_related("project").filter(public_id=campaign_id).first()
        )
        if campaign is None:
            return error("NOT_FOUND", "Campaign not found.", status=404)

        from jandrishti.modules.media.application.service import MediaService
        from jandrishti.modules.media.models import MediaAttachment

        expenses = list(campaign.expenses.all()[:200])
        context = {
            "request": request,
            "expense_media_map": MediaService.for_target(
                MediaAttachment.Target.EXPENSE, [e.id for e in expenses]
            ),
        }
        contributors = (
            campaign.contributions.filter(status=Contribution.Status.SUCCEEDED)
            .select_related("contributor")
            .order_by("-created_at")[:50]
        )
        return ok(
            {
                **CampaignSerializer(campaign).data,
                "expenses": ExpenseSerializer(expenses, many=True, context=context).data,
                "recent_contributors": [
                    {
                        "name": "Anonymous"
                        if c.is_anonymous or not c.contributor
                        else c.contributor.display_name,
                        "amount": str(c.amount),
                        "message": c.message,
                        "at": c.created_at,
                    }
                    for c in contributors
                ],
            }
        )


class ContributeView(ActorMixin, APIView):
    """Starts a contribution.

    While payments are disabled this returns 503 from the gateway adapter. That
    is deliberate: the spec forbids launching real-money collection without the
    surrounding legal and payment architecture, and a working-looking endpoint
    that quietly does nothing would be worse than a clear refusal.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request: Request, campaign_id: str) -> Response:
        if not settings.FUNDING_PAYMENTS_ENABLED:
            return error(
                "FEATURE_DISABLED",
                "Community funding is not accepting contributions on this deployment yet.",
                status=503,
                details={"reason": "Payment provider and legal entity not configured."},
            )

        campaign = FundingCampaign.objects.filter(public_id=campaign_id).first()
        if campaign is None:
            return error("NOT_FOUND", "Campaign not found.", status=404)

        # Reached only when a real gateway is registered; the abstraction is in
        # place so that day is a configuration change, not a rewrite.
        gateway = get_payment_gateway()
        intent = gateway.create_intent(
            amount=request.data.get("amount"),
            currency="INR",
            idempotency_key=f"{campaign.public_id}:{request.user.id}:{request.data.get('nonce', '')}",
            metadata={"campaign": str(campaign.public_id)},
        )
        return ok(
            {
                "reference": intent.reference,
                "checkout_url": intent.checkout_url,
                "provider": intent.provider,
            }
        )

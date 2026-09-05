"""
Verification endpoints.

Note what is absent: there is no endpoint that returns a document URL to the
public, and no serializer field anywhere carries an Aadhaar number. Private
document access is a separate, audited, moderator-only endpoint.
"""

from __future__ import annotations

from rest_framework import serializers
from rest_framework.generics import ListAPIView
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from jandrishti.modules.accounts.domain.enums import ProfessionalCategory
from jandrishti.modules.media.application.service import MediaService, UploadRequest
from jandrishti.shared.api.pagination import StandardPageNumberPagination
from jandrishti.shared.api.permissions import IsModerator
from jandrishti.shared.api.response import created, error, ok
from jandrishti.shared.api.throttling import ScopedActionThrottle
from jandrishti.shared.api.views import ActorMixin

from ..application.use_cases import (
    ReviewVerificationCommand,
    ReviewVerificationUseCase,
    SubmitVerificationCommand,
    SubmitVerificationUseCase,
)
from ..models import (
    DocumentAccessLog,
    ProfessionalVerification,
    VerificationDocument,
    VerificationMethod,
    VerificationStatus,
)


class DocumentInputSerializer(serializers.Serializer):
    media_id = serializers.UUIDField()
    kind = serializers.ChoiceField(
        choices=VerificationDocument.Kind.choices, default=VerificationDocument.Kind.OTHER
    )
    note = serializers.CharField(required=False, allow_blank=True, max_length=300)


class SubmitVerificationSerializer(serializers.Serializer):
    claimed_category = serializers.ChoiceField(choices=ProfessionalCategory.choices)
    method = serializers.ChoiceField(
        choices=VerificationMethod.choices, default=VerificationMethod.DOCUMENT
    )
    organization = serializers.CharField(required=False, allow_blank=True, max_length=200)
    designation = serializers.CharField(required=False, allow_blank=True, max_length=150)
    employee_reference = serializers.CharField(required=False, allow_blank=True, max_length=100)
    service_start_year = serializers.IntegerField(required=False, allow_null=True, min_value=1940)
    service_end_year = serializers.IntegerField(required=False, allow_null=True, min_value=1940)
    applicant_note = serializers.CharField(required=False, allow_blank=True, max_length=2000)
    documents = DocumentInputSerializer(many=True, required=False, default=list)

    # The Aadhaar fallback carries a provider reference, never a number. A
    # client that sends `aadhaar_number` gets it silently ignored, because this
    # serializer has no such field.
    aadhaar_reference = serializers.CharField(required=False, allow_blank=True, max_length=128)
    aadhaar_last4 = serializers.RegexField(r"^\d{4}$", required=False, allow_blank=True)
    aadhaar_provider = serializers.CharField(required=False, allow_blank=True, max_length=60)


class VerificationSerializer(serializers.ModelSerializer):
    """What the applicant sees about their own request."""

    id = serializers.UUIDField(source="public_id", read_only=True)
    document_count = serializers.SerializerMethodField()

    class Meta:
        model = ProfessionalVerification
        fields = [
            "id",
            "claimed_category",
            "method",
            "status",
            "organization",
            "designation",
            "applicant_note",
            "reviewer_note",
            "rejection_reason",
            "document_count",
            "aadhaar_last4",
            "reviewed_at",
            "created_at",
        ]
        read_only_fields = fields

    def get_document_count(self, obj: ProfessionalVerification) -> int:
        return obj.documents.count()


class ReviewQueueSerializer(VerificationSerializer):
    applicant = serializers.SerializerMethodField()

    class Meta(VerificationSerializer.Meta):
        fields = [*VerificationSerializer.Meta.fields, "applicant"]

    def get_applicant(self, obj: ProfessionalVerification) -> dict:
        return {
            "id": str(obj.user_id),
            "display_name": obj.user.display_name,
            "email": obj.user.email,
        }


class ReviewSerializer(serializers.Serializer):
    decision = serializers.ChoiceField(
        choices=[
            VerificationStatus.VERIFIED,
            VerificationStatus.REJECTED,
            VerificationStatus.MORE_INFO_REQUIRED,
        ]
    )
    reviewer_note = serializers.CharField(required=False, allow_blank=True, max_length=2000)
    rejection_reason = serializers.CharField(required=False, allow_blank=True, max_length=500)


class PrivateDocumentUploadView(ActorMixin, APIView):
    """Uploads a verification document straight into private storage.

    Separate from the general media endpoint so that `is_private=True` is not
    something a client can forget to ask for.
    """

    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]
    throttle_classes = [ScopedActionThrottle]
    throttle_scope = "verification"

    def post(self, request: Request) -> Response:
        media = MediaService().upload(
            UploadRequest(
                file=request.FILES.get("file"),
                uploaded_by=request.user,
                folder="verification",
                private=True,
            )
        )
        # Only the id comes back. There is no URL to leak.
        return created({"media_id": str(media.public_id), "filename": media.original_filename})


class SubmitVerificationView(ActorMixin, APIView):
    permission_classes = [IsAuthenticated]
    throttle_classes = [ScopedActionThrottle]
    throttle_scope = "verification"

    def post(self, request: Request) -> Response:
        serializer = SubmitVerificationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        verification = SubmitVerificationUseCase().execute(
            SubmitVerificationCommand(
                claimed_category=data["claimed_category"],
                method=data["method"],
                organization=data.get("organization", ""),
                designation=data.get("designation", ""),
                employee_reference=data.get("employee_reference", ""),
                service_start_year=data.get("service_start_year"),
                service_end_year=data.get("service_end_year"),
                applicant_note=data.get("applicant_note", ""),
                documents=[
                    {**doc, "media_id": str(doc["media_id"])} for doc in data.get("documents", [])
                ],
                aadhaar_reference=data.get("aadhaar_reference", ""),
                aadhaar_last4=data.get("aadhaar_last4", ""),
                aadhaar_provider=data.get("aadhaar_provider", ""),
                actor=self.get_actor(),
            )
        )
        return created(VerificationSerializer(verification).data)


class MyVerificationView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request: Request) -> Response:
        verification = (
            ProfessionalVerification.objects.filter(user=request.user)
            .order_by("-created_at")
            .first()
        )
        return ok(VerificationSerializer(verification).data if verification else None)


class ReviewQueueView(ListAPIView):
    permission_classes = [IsAuthenticated, IsModerator]
    serializer_class = ReviewQueueSerializer
    pagination_class = StandardPageNumberPagination
    queryset = (
        ProfessionalVerification.objects.select_related("user")
        .filter(status__in=[VerificationStatus.PENDING, VerificationStatus.MORE_INFO_REQUIRED])
        .order_by("created_at")
    )


class ReviewVerificationView(ActorMixin, APIView):
    permission_classes = [IsAuthenticated, IsModerator]

    def post(self, request: Request, verification_id: str) -> Response:
        serializer = ReviewSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        verification = ReviewVerificationUseCase().execute(
            ReviewVerificationCommand(
                verification_id=verification_id,
                decision=serializer.validated_data["decision"],
                reviewer_note=serializer.validated_data.get("reviewer_note", ""),
                rejection_reason=serializer.validated_data.get("rejection_reason", ""),
                actor=self.get_actor(),
            )
        )
        return ok(ReviewQueueSerializer(verification).data)


class DocumentAccessView(ActorMixin, APIView):
    """Time-limited access to one private document, for a reviewer.

    Audited before the URL is handed out, so the record exists even if the
    reviewer never opens it.
    """

    permission_classes = [IsAuthenticated, IsModerator]

    def get(self, request: Request, document_id: str) -> Response:
        document = (
            VerificationDocument.objects.select_related("media", "verification")
            .filter(public_id=document_id, purged_at__isnull=True)
            .first()
        )
        if document is None:
            return error("NOT_FOUND", "Document not found or no longer retained.", status=404)

        DocumentAccessLog.objects.create(
            document=document,
            accessed_by=request.user,
            ip_address=self.get_actor().ip_address or None,
            reason=request.query_params.get("reason", "")[:200],
        )
        from jandrishti.modules.audit.application.recorder import record_audit

        record_audit(
            action="verification.document_accessed",
            actor=request.user,
            target=f"verification_document:{document.public_id}",
            metadata={"verification": str(document.verification.public_id)},
            ip_address=self.get_actor().ip_address or None,
        )

        url = MediaService().signed_url(document.media, expires_in=300)
        return ok({"url": url, "expires_in": 300, "kind": document.kind})

"""Upload endpoint and the public media serializer."""

from __future__ import annotations

from rest_framework import serializers
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from jandrishti.shared.api.response import created
from jandrishti.shared.api.throttling import ScopedActionThrottle
from jandrishti.shared.api.views import ActorMixin

from ..application.service import MediaService, UploadRequest
from ..models import Media, MediaPurpose


class MediaSerializer(serializers.ModelSerializer):
    """What the public sees about a file.

    `verification_status` is included deliberately: the interface has to be able
    to distinguish uploaded evidence from verified evidence (spec 17).
    """

    id = serializers.UUIDField(source="public_id", read_only=True)
    uploaded_by_name = serializers.CharField(source="uploaded_by.display_name", default="")

    class Meta:
        model = Media
        fields = [
            "id",
            "media_type",
            "purpose",
            "url",
            "thumbnail_url",
            "caption",
            "mime_type",
            "file_size",
            "width",
            "height",
            "duration_seconds",
            "verification_status",
            "verified_at",
            "captured_at",
            "uploaded_by_name",
            "created_at",
        ]
        read_only_fields = fields


class MediaUploadView(ActorMixin, APIView):
    """POST a file, get back a media id to attach to a form submission."""

    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]
    throttle_classes = [ScopedActionThrottle]
    throttle_scope = "upload"

    def post(self, request: Request) -> Response:
        purpose = request.data.get("purpose", MediaPurpose.GENERAL)
        if purpose not in MediaPurpose.values:
            purpose = MediaPurpose.GENERAL

        media = MediaService().upload(
            UploadRequest(
                file=request.FILES.get("file"),
                uploaded_by=request.user,
                purpose=purpose,
                caption=request.data.get("caption", "")[:300],
                folder=request.data.get("folder", "general")[:40],
            )
        )
        return created(MediaSerializer(media).data)

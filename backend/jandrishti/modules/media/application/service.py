"""
MediaService: upload validation and attachment.

Every upload is validated here, on the server, against the declared type *and*
the actual bytes. Trusting the browser-supplied content type is how a `.php`
arrives named `photo.jpg`.
"""

from __future__ import annotations

import hashlib
import logging
from dataclasses import dataclass
from typing import Any, BinaryIO

from django.conf import settings
from django.core.files.uploadedfile import UploadedFile

from jandrishti.shared.domain.exceptions import ValidationError

from ..domain.ports import MediaStorage
from ..infrastructure.storage import get_media_storage
from ..models import Media, MediaAttachment, MediaPurpose, MediaType

logger = logging.getLogger(__name__)

# Magic bytes for the formats we accept. The declared MIME type must agree with
# what the file actually starts with.
MAGIC_SIGNATURES: dict[str, tuple[bytes, ...]] = {
    "image/jpeg": (b"\xff\xd8\xff",),
    "image/png": (b"\x89PNG\r\n\x1a\n",),
    "image/webp": (b"RIFF",),
    "application/pdf": (b"%PDF-",),
    "video/mp4": (b"\x00\x00\x00",),
    "video/quicktime": (b"\x00\x00\x00",),
    "video/webm": (b"\x1a\x45\xdf\xa3",),
}

MIME_TO_TYPE = {
    **{mime: MediaType.IMAGE for mime in settings.ALLOWED_IMAGE_MIME_TYPES},
    **{mime: MediaType.VIDEO for mime in settings.ALLOWED_VIDEO_MIME_TYPES},
    **{mime: MediaType.DOCUMENT for mime in settings.ALLOWED_DOCUMENT_MIME_TYPES},
}

SIZE_LIMITS = {
    MediaType.IMAGE: settings.MAX_UPLOAD_SIZE_IMAGE,
    MediaType.VIDEO: settings.MAX_UPLOAD_SIZE_VIDEO,
    MediaType.DOCUMENT: settings.MAX_UPLOAD_SIZE_DOCUMENT,
}

RESOURCE_TYPES = {
    MediaType.IMAGE: "image",
    MediaType.VIDEO: "video",
    MediaType.DOCUMENT: "raw",
    MediaType.AUDIO: "video",
}


@dataclass(slots=True)
class UploadRequest:
    file: UploadedFile
    uploaded_by: Any
    purpose: str = MediaPurpose.GENERAL
    caption: str = ""
    folder: str = "general"
    private: bool = False


class MediaService:
    def __init__(self, storage: MediaStorage | None = None) -> None:
        self._storage = storage or get_media_storage()

    # -- validation ---------------------------------------------------------

    def validate(self, file: UploadedFile) -> MediaType:
        if not file or not file.name:
            raise ValidationError("No file was provided.")

        mime = (file.content_type or "").lower().split(";")[0].strip()
        media_type = MIME_TO_TYPE.get(mime)
        if media_type is None:
            raise ValidationError(
                "That file type is not supported.",
                details={"allowed": sorted(MIME_TO_TYPE)},
            )

        limit = SIZE_LIMITS[media_type]
        if file.size > limit:
            raise ValidationError(
                f"File is too large. The limit for this type is {limit // (1024 * 1024)} MB.",
                details={"size": file.size, "limit": limit},
            )

        self._assert_magic_bytes(file, mime)
        return media_type

    @staticmethod
    def _assert_magic_bytes(file: UploadedFile, mime: str) -> None:
        signatures = MAGIC_SIGNATURES.get(mime)
        if not signatures:
            return
        file.seek(0)
        header = file.read(16)
        file.seek(0)
        # MP4 and QuickTime carry `ftyp` at offset 4 rather than at the start.
        if mime in {"video/mp4", "video/quicktime"}:
            if b"ftyp" not in header:
                raise ValidationError("The file contents do not match a video file.")
            return
        if not any(header.startswith(sig) for sig in signatures):
            raise ValidationError("The file contents do not match its declared type.")

    @staticmethod
    def _checksum(file: BinaryIO) -> str:
        """SHA-256 of the upload, used to spot the same photo posted twice."""
        digest = hashlib.sha256()
        file.seek(0)
        for chunk in iter(lambda: file.read(8192), b""):
            digest.update(chunk)
        file.seek(0)
        return digest.hexdigest()

    # -- commands -----------------------------------------------------------

    def upload(self, request: UploadRequest) -> Media:
        media_type = self.validate(request.file)
        checksum = self._checksum(request.file)

        stored = self._storage.upload(
            request.file,
            folder=request.folder,
            filename=request.file.name,
            resource_type=RESOURCE_TYPES[media_type],
            private=request.private,
        )

        media = Media.objects.create(
            media_type=media_type,
            purpose=request.purpose,
            storage_backend=stored.backend,
            storage_key=stored.storage_key,
            url=stored.url,
            thumbnail_url=stored.thumbnail_url,
            mime_type=(request.file.content_type or "").split(";")[0],
            file_size=stored.file_size or request.file.size,
            original_filename=request.file.name[:255],
            width=stored.width,
            height=stored.height,
            duration_seconds=stored.duration_seconds,
            checksum=checksum,
            uploaded_by=request.uploaded_by,
            caption=request.caption[:300],
            is_private=request.private,
        )
        logger.info(
            "media uploaded",
            extra={"media_id": str(media.public_id), "type": media_type, "backend": stored.backend},
        )
        return media

    def attach(
        self,
        media_ids: list[str],
        *,
        target_type: str,
        target_id: int,
        owner: Any = None,
    ) -> int:
        """Link already-uploaded media to a target.

        Uploading and attaching are separate steps so the browser can upload
        while the user is still typing, and so a half-filled form does not lose
        the files. Ownership is re-checked here: you may only attach media you
        uploaded, which stops one user from stapling another user's evidence
        onto their own report.
        """
        if not media_ids:
            return 0
        queryset = Media.objects.filter(public_id__in=media_ids[:30])
        if owner is not None:
            queryset = queryset.filter(uploaded_by=owner)

        found = list(queryset)
        if len(found) != len(set(media_ids[:30])):
            raise ValidationError("Some of the attached files could not be found.")

        MediaAttachment.objects.bulk_create(
            [
                MediaAttachment(
                    media=media,
                    target_type=target_type,
                    target_id=target_id,
                    display_order=index,
                )
                for index, media in enumerate(found)
            ],
            ignore_conflicts=True,
        )
        return len(found)

    @staticmethod
    def for_target(target_type: str, target_ids: list[int]) -> dict[int, list[Media]]:
        """Media for many targets in one query -- the N+1 guard for list views."""
        attachments = (
            MediaAttachment.objects.filter(target_type=target_type, target_id__in=target_ids)
            .select_related("media")
            .order_by("display_order", "created_at")
        )
        grouped: dict[int, list[Media]] = {}
        for attachment in attachments:
            if not attachment.media.is_private:
                grouped.setdefault(attachment.target_id, []).append(attachment.media)
        return grouped

    def signed_url(self, media: Media, expires_in: int = 300) -> str:
        return self._storage.signed_url(media.storage_key, expires_in=expires_in)


media_service = MediaService()

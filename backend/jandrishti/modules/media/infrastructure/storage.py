"""
Storage adapters.

`get_media_storage()` picks Cloudinary when it is configured and the local
filesystem otherwise, so a developer can clone the repo and upload evidence
without signing up for anything. Both satisfy the same port.
"""

from __future__ import annotations

import logging
import os
import uuid
from typing import BinaryIO

from django.conf import settings
from django.core.files.storage import default_storage

from jandrishti.shared.domain.exceptions import ExternalServiceError

from ..domain.ports import StoredFile

logger = logging.getLogger(__name__)


class LocalMediaStorage:
    """Filesystem adapter. Development and self-hosted deployments."""

    name = "local"

    def upload(
        self, file: BinaryIO, *, folder: str, filename: str, resource_type: str, private: bool
    ) -> StoredFile:
        extension = os.path.splitext(filename)[1][:10]
        prefix = "private" if private else "public"
        key = f"{prefix}/{folder}/{uuid.uuid4().hex}{extension}"
        saved_key = default_storage.save(key, file)
        size = default_storage.size(saved_key)
        return StoredFile(
            storage_key=saved_key,
            # Private files get no directly usable URL; callers must go through
            # the authorized download endpoint.
            url="" if private else default_storage.url(saved_key),
            backend=self.name,
            file_size=size,
        )

    def delete(self, storage_key: str, *, resource_type: str = "image") -> None:
        if default_storage.exists(storage_key):
            default_storage.delete(storage_key)

    def signed_url(self, storage_key: str, *, expires_in: int = 300) -> str:
        # The local backend has no signing; the API streams the bytes instead
        # after checking permissions.
        return ""


class CloudinaryMediaStorage:
    """Cloudinary adapter.

    Private assets are uploaded to a restricted type so that guessing the URL
    is not enough to read a verification document -- access requires a signed,
    short-lived URL that only an authorized request can obtain.
    """

    name = "cloudinary"

    def __init__(self) -> None:
        import cloudinary

        cloudinary.config(
            cloud_name=settings.CLOUDINARY_CLOUD_NAME,
            api_key=settings.CLOUDINARY_API_KEY,
            api_secret=settings.CLOUDINARY_API_SECRET,
            secure=True,
        )
        self._cloudinary = cloudinary

    def upload(
        self, file: BinaryIO, *, folder: str, filename: str, resource_type: str, private: bool
    ) -> StoredFile:
        import cloudinary.uploader

        try:
            result = cloudinary.uploader.upload(
                file,
                folder=f"jandrishti/{folder}",
                resource_type=resource_type,
                type="authenticated" if private else "upload",
                unique_filename=True,
                overwrite=False,
                use_filename=False,
            )
        except Exception as exc:
            logger.exception("cloudinary upload failed", extra={"folder": folder})
            raise ExternalServiceError("Upload failed. Please try again.") from exc

        return StoredFile(
            storage_key=result["public_id"],
            url="" if private else result.get("secure_url", ""),
            backend=self.name,
            thumbnail_url=self._thumbnail(result) if not private else "",
            width=result.get("width"),
            height=result.get("height"),
            duration_seconds=result.get("duration"),
            file_size=result.get("bytes", 0),
        )

    def _thumbnail(self, result: dict) -> str:
        from cloudinary import CloudinaryImage

        if result.get("resource_type") != "image":
            return ""
        return CloudinaryImage(result["public_id"]).build_url(
            width=480, height=320, crop="fill", quality="auto", fetch_format="auto"
        )

    def delete(self, storage_key: str, *, resource_type: str = "image") -> None:
        import cloudinary.uploader

        try:
            cloudinary.uploader.destroy(storage_key, resource_type=resource_type)
        except Exception:
            logger.exception("cloudinary delete failed", extra={"storage_key": storage_key})

    def signed_url(self, storage_key: str, *, expires_in: int = 300) -> str:
        import time

        from cloudinary.utils import cloudinary_url

        url, _ = cloudinary_url(
            storage_key,
            type="authenticated",
            sign_url=True,
            secure=True,
            expires_at=int(time.time()) + expires_in,
        )
        return url


def get_media_storage():
    """Adapter selection. The only place this decision is made."""
    if settings.CLOUDINARY_CLOUD_NAME and settings.CLOUDINARY_API_KEY:
        return CloudinaryMediaStorage()
    logger.info("Cloudinary is not configured; using local media storage.")
    return LocalMediaStorage()

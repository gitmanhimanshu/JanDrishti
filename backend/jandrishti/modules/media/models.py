"""
Media (spec 16, 17).

One `Media` row per uploaded file, and separate link tables joining media to
whatever it documents. No `photo1 / photo2 / photo3` columns anywhere: a
problem can carry unlimited evidence, and the join table is what makes that
true without a schema change.

PostgreSQL stores the reference; the bytes live in Cloudinary or on disk.
"""

from __future__ import annotations

from django.conf import settings
from django.db import models

from jandrishti.shared.models import BaseEntity


class MediaType(models.TextChoices):
    IMAGE = "IMAGE", "Image"
    VIDEO = "VIDEO", "Video"
    DOCUMENT = "DOCUMENT", "Document"
    AUDIO = "AUDIO", "Audio"


class MediaPurpose(models.TextChoices):
    """What this file is meant to show.

    BEFORE / DURING / AFTER are what make a proof-of-work timeline legible: the
    same location, photographed at three points in the lifecycle (spec 34).
    """

    GENERAL = "GENERAL", "General"
    BEFORE = "BEFORE", "Before"
    DURING = "DURING", "During"
    AFTER = "AFTER", "After"
    EVIDENCE = "EVIDENCE", "Evidence"
    DOCUMENT = "DOCUMENT", "Document"


class VerificationStatus(models.TextChoices):
    """Uploading is not verifying (spec 17).

    The public UI must show the difference, and nothing here is ever set to
    VERIFIED by an automated process.
    """

    UPLOADED = "UPLOADED", "Uploaded"
    UNDER_VERIFICATION = "UNDER_VERIFICATION", "Under verification"
    VERIFIED = "VERIFIED", "Verified"
    REJECTED = "REJECTED", "Rejected"


class Media(BaseEntity):
    media_type = models.CharField(max_length=20, choices=MediaType.choices, db_index=True)
    purpose = models.CharField(
        max_length=20, choices=MediaPurpose.choices, default=MediaPurpose.GENERAL, db_index=True
    )

    # Storage reference. `storage_key` is provider-specific (a Cloudinary public
    # id, or a relative path on disk); `url` is what the client renders.
    storage_backend = models.CharField(max_length=40, default="cloudinary")
    storage_key = models.CharField(max_length=300, db_index=True)
    url = models.URLField(max_length=800)
    thumbnail_url = models.URLField(max_length=800, blank=True)

    mime_type = models.CharField(max_length=100)
    file_size = models.PositiveBigIntegerField(default=0)
    original_filename = models.CharField(max_length=255, blank=True)
    width = models.PositiveIntegerField(null=True, blank=True)
    height = models.PositiveIntegerField(null=True, blank=True)
    duration_seconds = models.FloatField(null=True, blank=True)
    checksum = models.CharField(max_length=64, blank=True, db_index=True)

    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="uploaded_media",
    )
    caption = models.CharField(max_length=300, blank=True)

    verification_status = models.CharField(
        max_length=25,
        choices=VerificationStatus.choices,
        default=VerificationStatus.UPLOADED,
        db_index=True,
    )
    verified_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="verified_media",
    )
    verified_at = models.DateTimeField(null=True, blank=True)
    verification_note = models.CharField(max_length=500, blank=True)

    # EXIF-derived capture context, when the uploader allows it. Useful
    # corroboration for a claim about where and when something was seen.
    captured_at = models.DateTimeField(null=True, blank=True)
    latitude = models.FloatField(null=True, blank=True)
    longitude = models.FloatField(null=True, blank=True)

    # Private media (verification documents) is never served publicly; it is
    # reachable only through an authorized, audited endpoint.
    is_private = models.BooleanField(default=False, db_index=True)

    class Meta:
        db_table = "media_asset"
        ordering = ["created_at"]
        indexes = [
            models.Index(fields=["media_type", "verification_status"]),
            models.Index(fields=["uploaded_by", "-created_at"]),
        ]

    def __str__(self) -> str:
        return f"{self.media_type}:{self.storage_key}"

    @property
    def is_verified(self) -> bool:
        return self.verification_status == VerificationStatus.VERIFIED


class MediaAttachment(BaseEntity):
    """Join between a Media row and the thing it documents.

    A generic link table keeps every attachment path identical -- problems,
    experiences, project updates and expense receipts all attach the same way,
    and adding a fifth attachable kind needs no new table.
    """

    class Target(models.TextChoices):
        PROBLEM = "PROBLEM", "Problem"
        EXPERIENCE = "EXPERIENCE", "Experience"
        PROJECT_UPDATE = "PROJECT_UPDATE", "Project update"
        EXPENSE = "EXPENSE", "Expense"
        GOVERNMENT_RESPONSE = "GOVERNMENT_RESPONSE", "Government response"
        VERIFICATION = "VERIFICATION", "Professional verification"

    media = models.ForeignKey(Media, on_delete=models.CASCADE, related_name="attachments")
    target_type = models.CharField(max_length=30, choices=Target.choices, db_index=True)
    target_id = models.BigIntegerField(db_index=True)
    display_order = models.PositiveIntegerField(default=0)

    class Meta:
        db_table = "media_attachment"
        ordering = ["display_order", "created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["media", "target_type", "target_id"], name="uq_media_attachment"
            )
        ]
        indexes = [models.Index(fields=["target_type", "target_id", "display_order"])]

    def __str__(self) -> str:
        return f"{self.target_type}#{self.target_id} <- media {self.media_id}"

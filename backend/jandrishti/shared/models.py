"""
Abstract model bases every module builds on.

Public identifiers are UUIDs: sequential integers in a public URL leak how many
problems have ever been reported and make scraping trivial. The integer primary
key is kept for join performance and never appears in an API response.
"""

from __future__ import annotations

import uuid

from django.db import models
from django.utils import timezone


class TimeStampedModel(models.Model):
    created_at = models.DateTimeField(default=timezone.now, editable=False, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class PublicIdModel(models.Model):
    """Adds the opaque identifier used in every public URL and API payload."""

    public_id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False, db_index=True)

    class Meta:
        abstract = True


class SoftDeleteQuerySet(models.QuerySet):
    def alive(self) -> SoftDeleteQuerySet:
        return self.filter(deleted_at__isnull=True)

    def dead(self) -> SoftDeleteQuerySet:
        return self.filter(deleted_at__isnull=False)

    def delete(self):  # type: ignore[override]
        return self.update(deleted_at=timezone.now())

    def hard_delete(self):
        return super().delete()


class SoftDeleteManager(models.Manager.from_queryset(SoftDeleteQuerySet)):  # type: ignore[misc]
    """Default manager hides soft-deleted rows; `all_objects` still sees them.

    Citizen reports are civic record. Removing one hides it from the public site
    but keeps it available to moderation and audit, which is what section 19
    means by never deleting the original reports.
    """

    def get_queryset(self) -> SoftDeleteQuerySet:
        return super().get_queryset().filter(deleted_at__isnull=True)


class SoftDeleteModel(models.Model):
    deleted_at = models.DateTimeField(null=True, blank=True, db_index=True)

    objects = SoftDeleteManager()
    all_objects = models.Manager.from_queryset(SoftDeleteQuerySet)()

    class Meta:
        abstract = True

    def soft_delete(self) -> None:
        self.deleted_at = timezone.now()
        self.save(update_fields=["deleted_at", "updated_at"])

    def restore(self) -> None:
        self.deleted_at = None
        self.save(update_fields=["deleted_at", "updated_at"])


class BaseEntity(TimeStampedModel, PublicIdModel):
    """The usual combination: timestamps plus a public UUID."""

    class Meta:
        abstract = True


class LocatedModel(models.Model):
    """Indian administrative location plus optional GPS.

    Latitude and longitude are indexed together so the bounding-box prefilter
    behind `nearby` and duplicate detection stays index-served at scale.
    """

    address = models.CharField(max_length=500, blank=True)
    city = models.CharField(max_length=120, blank=True, db_index=True)
    district = models.CharField(max_length=120, blank=True, db_index=True)
    state = models.CharField(max_length=120, blank=True, db_index=True)
    pincode = models.CharField(max_length=6, blank=True, db_index=True)
    latitude = models.FloatField(null=True, blank=True)
    longitude = models.FloatField(null=True, blank=True)

    class Meta:
        abstract = True
        indexes = [models.Index(fields=["latitude", "longitude"])]

    @property
    def has_coordinates(self) -> bool:
        return self.latitude is not None and self.longitude is not None

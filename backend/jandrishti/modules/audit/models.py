"""
Audit log (spec 63).

Append-only by convention and by permission: no API exposes update or delete,
and only administrators can read it. The rows that matter most are the ones
nobody wants to be caught changing -- role grants, verification decisions,
problem status changes and access to sensitive documents.
"""

from __future__ import annotations

from django.conf import settings
from django.db import models

from jandrishti.shared.models import TimeStampedModel


class AuditLog(TimeStampedModel):
    action = models.CharField(max_length=100, db_index=True)
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="audit_entries",
    )
    # Kept as text so a deleted actor still leaves a legible trail.
    actor_label = models.CharField(max_length=150, blank=True)
    target = models.CharField(max_length=200, blank=True, db_index=True)
    metadata = models.JSONField(default=dict, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    request_id = models.CharField(max_length=64, blank=True)

    class Meta:
        db_table = "audit_log"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["action", "-created_at"]),
            models.Index(fields=["target", "-created_at"]),
        ]

    def __str__(self) -> str:
        return f"{self.action} by {self.actor_label or 'system'}"

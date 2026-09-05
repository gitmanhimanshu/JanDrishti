"""
Refresh tokens and OAuth state.

Access tokens are short-lived, stateless JWTs. Refresh tokens are long-lived,
so they are stored (hashed) and rotated on every use: a stolen refresh token
that is replayed after the legitimate client has rotated it is detected, and
the whole token family is revoked.
"""

from __future__ import annotations

import hashlib
import secrets
from datetime import timedelta

from django.conf import settings
from django.db import models
from django.utils import timezone

from jandrishti.shared.models import TimeStampedModel


def hash_token(raw: str) -> str:
    """Refresh tokens are stored as digests -- a database leak is not a session leak."""
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


class RefreshToken(TimeStampedModel):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="refresh_tokens"
    )
    token_hash = models.CharField(max_length=64, unique=True, db_index=True)
    # All rotations of one login share a family id, so detecting replay lets us
    # revoke exactly that login and nothing else.
    family = models.UUIDField(db_index=True)
    expires_at = models.DateTimeField(db_index=True)
    revoked_at = models.DateTimeField(null=True, blank=True)
    replaced_by = models.CharField(max_length=64, blank=True)
    user_agent = models.CharField(max_length=300, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)

    class Meta:
        db_table = "auth_refresh_token"
        indexes = [models.Index(fields=["user", "revoked_at"])]

    @property
    def is_active(self) -> bool:
        return self.revoked_at is None and self.expires_at > timezone.now()

    @classmethod
    def issue(cls, user, family=None, user_agent: str = "", ip_address: str | None = None):
        """Mint a new refresh token; returns (raw_token, row)."""
        import uuid

        raw = secrets.token_urlsafe(48)
        row = cls.objects.create(
            user=user,
            token_hash=hash_token(raw),
            family=family or uuid.uuid4(),
            expires_at=timezone.now() + settings.JWT_REFRESH_TTL,
            user_agent=user_agent[:300],
            ip_address=ip_address or None,
        )
        return raw, row

    def revoke(self, replaced_by: str = "") -> None:
        self.revoked_at = timezone.now()
        self.replaced_by = replaced_by
        self.save(update_fields=["revoked_at", "replaced_by", "updated_at"])

    @classmethod
    def revoke_family(cls, family) -> int:
        return cls.objects.filter(family=family, revoked_at__isnull=True).update(
            revoked_at=timezone.now()
        )


class OAuthState(models.Model):
    """Single-use CSRF state for the OAuth redirect.

    Also carries `next_path`, which is how the user lands back on the problem
    they were trying to support instead of on the home page (spec 5).
    """

    state = models.CharField(max_length=64, primary_key=True)
    next_path = models.CharField(max_length=500, blank=True)
    created_at = models.DateTimeField(default=timezone.now)
    consumed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "auth_oauth_state"

    def __str__(self) -> str:
        return f"oauth-state:{self.state[:8]}…"

    @classmethod
    def create(cls, next_path: str = "") -> OAuthState:
        return cls.objects.create(state=secrets.token_urlsafe(32), next_path=next_path[:500])

    @property
    def is_usable(self) -> bool:
        return self.consumed_at is None and self.created_at > timezone.now() - timedelta(minutes=10)

    def consume(self) -> None:
        self.consumed_at = timezone.now()
        self.save(update_fields=["consumed_at"])

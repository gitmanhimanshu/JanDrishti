"""
Rate limiting.

Different actions deserve different limits: browsing is cheap, reporting a
problem is not, and submitting verification documents least of all. Limits are
declared per view via `throttle_scope` and enforced against Redis in production.
"""

from __future__ import annotations

from rest_framework.throttling import ScopedRateThrottle, SimpleRateThrottle


class ScopedActionThrottle(ScopedRateThrottle):
    """Per-user (or per-IP when anonymous) limit for a named scope."""

    def get_cache_key(self, request, view):  # type: ignore[no-untyped-def]
        scope = getattr(view, self.scope_attr, None)
        if not scope:
            return None
        self.scope = scope
        self.rate = self.get_rate()
        self.num_requests, self.duration = self.parse_rate(self.rate)
        ident = (
            str(request.user.pk)
            if request.user and request.user.is_authenticated
            else self.get_ident(request)
        )
        return f"throttle:{scope}:{ident}"


class AuthEndpointThrottle(SimpleRateThrottle):
    """Guards the OAuth exchange endpoints against credential stuffing."""

    scope = "auth"

    def get_cache_key(self, request, view):  # type: ignore[no-untyped-def]
        return f"throttle:auth:{self.get_ident(request)}"

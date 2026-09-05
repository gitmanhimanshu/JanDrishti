"""Shared view base classes and the health probe."""

from __future__ import annotations

from typing import Any

from django.core.cache import cache
from django.db import connection
from django.http import HttpRequest, JsonResponse
from django.views.decorators.http import require_GET
from rest_framework.request import Request

from ..application.use_case import Actor


@require_GET
def health_view(request: HttpRequest) -> JsonResponse:
    """Liveness plus dependency check, for the load balancer and for humans."""
    checks: dict[str, str] = {}
    status = 200
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
        checks["database"] = "ok"
    except Exception:
        checks["database"] = "error"
        status = 503
    try:
        cache.set("health:probe", "1", 5)
        checks["cache"] = "ok" if cache.get("health:probe") == "1" else "degraded"
    except Exception:
        checks["cache"] = "error"
        status = 503
    return JsonResponse({"success": status == 200, "data": {"checks": checks}}, status=status)


class ActorMixin:
    """Turns an HTTP request into the Actor the application layer expects.

    This is the boundary: below it, nothing knows what a request is.
    """

    def get_actor(self: Any) -> Actor:
        request: Request = self.request
        user = request.user if getattr(request, "user", None) else None
        return Actor(
            user=user if getattr(user, "is_authenticated", False) else None,
            ip_address=_client_ip(request),
            user_agent=request.META.get("HTTP_USER_AGENT", "")[:300],
            request_id=getattr(request, "request_id", ""),
        )


def _client_ip(request: Any) -> str:
    forwarded = request.META.get("HTTP_X_FORWARDED_FOR", "")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR", "")

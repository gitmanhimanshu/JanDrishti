"""Attaches a request id and basic latency telemetry to every request."""

from __future__ import annotations

import logging
import time
import uuid
from collections.abc import Callable

from django.http import HttpRequest, HttpResponse

logger = logging.getLogger("jandrishti.request")


class RequestContextMiddleware:
    """Correlation id in, structured access log out.

    The id is echoed as X-Request-ID so a user reporting a failure can be traced
    to the exact server-side log line without exposing anything about it.
    """

    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]) -> None:
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        request_id = request.headers.get("X-Request-ID") or uuid.uuid4().hex
        request.request_id = request_id  # type: ignore[attr-defined]
        started = time.perf_counter()

        response = self.get_response(request)

        duration_ms = round((time.perf_counter() - started) * 1000, 2)
        response["X-Request-ID"] = request_id
        if not request.path.startswith(("/static/", "/media/", "/health")):
            logger.info(
                "request",
                extra={
                    "request_id": request_id,
                    "method": request.method,
                    "path": request.path,
                    "status": response.status_code,
                    "duration_ms": duration_ms,
                    "authenticated": bool(
                        getattr(getattr(request, "user", None), "is_authenticated", False)
                    ),
                },
            )
        return response

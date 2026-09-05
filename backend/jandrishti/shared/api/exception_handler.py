"""
One place where an exception becomes an HTTP response.

Domain errors carry their own code and status, so a use case can raise
`IllegalStateTransitionError` without ever importing `rest_framework`. Anything
unrecognised becomes a generic 500 -- stack traces do not leave the server.
"""

from __future__ import annotations

import logging
from typing import Any

from django.core.exceptions import PermissionDenied as DjangoPermissionDenied
from django.core.exceptions import ValidationError as DjangoValidationError
from django.http import Http404
from rest_framework import exceptions as drf_exceptions
from rest_framework.response import Response
from rest_framework.views import exception_handler as drf_exception_handler

from ...shared.domain.exceptions import DomainError

logger = logging.getLogger(__name__)

# DRF exception class -> stable machine readable code for the frontend.
DRF_CODES: dict[type, str] = {
    drf_exceptions.NotAuthenticated: "AUTHENTICATION_REQUIRED",
    drf_exceptions.AuthenticationFailed: "AUTHENTICATION_FAILED",
    drf_exceptions.PermissionDenied: "PERMISSION_DENIED",
    drf_exceptions.NotFound: "NOT_FOUND",
    drf_exceptions.MethodNotAllowed: "METHOD_NOT_ALLOWED",
    drf_exceptions.Throttled: "RATE_LIMITED",
    drf_exceptions.ParseError: "MALFORMED_REQUEST",
    drf_exceptions.UnsupportedMediaType: "UNSUPPORTED_MEDIA_TYPE",
    drf_exceptions.ValidationError: "VALIDATION_ERROR",
}


def _envelope(code: str, message: str, details: Any = None) -> dict[str, Any]:
    body: dict[str, Any] = {"success": False, "error": {"code": code, "message": message}}
    if details:
        body["error"]["details"] = details
    return body


def api_exception_handler(exc: Exception, context: dict[str, Any]) -> Response | None:
    if isinstance(exc, DomainError):
        return Response(
            _envelope(exc.code, exc.message, exc.details or None), status=exc.status_code
        )

    if isinstance(exc, Http404):
        return Response(_envelope("NOT_FOUND", "Resource not found."), status=404)

    if isinstance(exc, DjangoPermissionDenied):
        return Response(
            _envelope("PERMISSION_DENIED", "You do not have access to this action."), status=403
        )

    if isinstance(exc, DjangoValidationError):
        return Response(
            _envelope(
                "VALIDATION_ERROR",
                "The submitted data is invalid.",
                exc.message_dict if hasattr(exc, "message_dict") else {"errors": exc.messages},
            ),
            status=400,
        )

    response = drf_exception_handler(exc, context)
    if response is not None:
        code = DRF_CODES.get(type(exc), "REQUEST_ERROR")
        if isinstance(exc, drf_exceptions.ValidationError):
            message = "The submitted data is invalid."
            details = (
                response.data if isinstance(response.data, dict) else {"errors": response.data}
            )
        else:
            detail = getattr(exc, "detail", None)
            message = str(detail) if detail else "Request could not be completed."
            details = None
        response.data = _envelope(code, message, details)
        return response

    # Unhandled: log with full context server side, tell the client nothing.
    request = context.get("request")
    logger.exception(
        "unhandled exception",
        extra={
            "path": getattr(request, "path", ""),
            "method": getattr(request, "method", ""),
            "request_id": getattr(request, "request_id", ""),
        },
    )
    return Response(
        _envelope("INTERNAL_ERROR", "Something went wrong. Please try again."), status=500
    )

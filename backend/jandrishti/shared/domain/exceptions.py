"""
Domain level errors.

The domain layer knows nothing about HTTP. It raises these; the presentation
layer translates them into the API error envelope (shared/api/exception_handler).
That translation is the only place a status code is decided.
"""

from __future__ import annotations

from typing import Any


class DomainError(Exception):
    """Base class for every error the domain can raise."""

    code = "DOMAIN_ERROR"
    status_code = 400

    def __init__(self, message: str | None = None, *, details: dict[str, Any] | None = None):
        self.message = message or self.__class__.__doc__ or self.code
        self.details = details or {}
        super().__init__(self.message)


class ValidationError(DomainError):
    """The supplied data violates a business rule."""

    code = "VALIDATION_ERROR"
    status_code = 400


class NotFoundError(DomainError):
    """The requested resource does not exist."""

    code = "NOT_FOUND"
    status_code = 404


class PermissionDeniedError(DomainError):
    """The actor is not allowed to perform this action."""

    code = "PERMISSION_DENIED"
    status_code = 403


class AuthenticationRequiredError(DomainError):
    """This action requires a signed-in JanDrishti account."""

    code = "AUTHENTICATION_REQUIRED"
    status_code = 401


class ConflictError(DomainError):
    """The action conflicts with the current state of the resource."""

    code = "CONFLICT"
    status_code = 409


class IllegalStateTransitionError(ConflictError):
    """The requested status transition is not allowed from the current status."""

    code = "ILLEGAL_STATE_TRANSITION"
    status_code = 409


class RateLimitedError(DomainError):
    """Too many requests."""

    code = "RATE_LIMITED"
    status_code = 429


class FeatureDisabledError(DomainError):
    """The feature is deliberately switched off in this deployment."""

    code = "FEATURE_DISABLED"
    status_code = 503


class ExternalServiceError(DomainError):
    """A dependency outside JanDrishti failed."""

    code = "EXTERNAL_SERVICE_ERROR"
    status_code = 502

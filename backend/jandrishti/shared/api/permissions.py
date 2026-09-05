"""
Authorization primitives.

Two rules hold everywhere:

1. Reading public content never requires a login (spec 4).
2. Every write is authorized on the server, against the role stored on the
   user row -- never against a role the client sent (spec 8).
"""

from __future__ import annotations

from typing import Any

from rest_framework import permissions
from rest_framework.request import Request
from rest_framework.views import APIView


class PublicReadAuthenticatedWrite(permissions.BasePermission):
    """Anonymous GET/HEAD/OPTIONS; any write needs an account."""

    message = "You need a JanDrishti account to do this."

    def has_permission(self, request: Request, view: APIView) -> bool:
        if request.method in permissions.SAFE_METHODS:
            return True
        return bool(request.user and request.user.is_authenticated)


class IsOwnerOrReadOnly(permissions.BasePermission):
    """Object-level guard against IDOR on edit and delete."""

    message = "You can only modify content you created."
    owner_fields = ("author_id", "user_id", "created_by_id", "owner_id")

    def has_object_permission(self, request: Request, view: APIView, obj: Any) -> bool:
        if request.method in permissions.SAFE_METHODS:
            return True
        if not (request.user and request.user.is_authenticated):
            return False
        if getattr(request.user, "is_staff_role", False):
            return True
        return any(
            getattr(obj, field, None) == request.user.id
            for field in self.owner_fields
            if hasattr(obj, field)
        )


class RolePermission(permissions.BasePermission):
    """Base for role gates. Subclasses declare `allowed_roles`."""

    allowed_roles: tuple[str, ...] = ()
    message = "Your account does not have access to this area."

    def has_permission(self, request: Request, view: APIView) -> bool:
        user = request.user
        if not (user and user.is_authenticated):
            return False
        if getattr(user, "is_superuser", False):
            return True
        return getattr(user, "role", None) in self.allowed_roles


class IsGovernmentOfficial(RolePermission):
    allowed_roles = ("GOVERNMENT_OFFICIAL", "ADMIN")
    message = "This dashboard is for verified government officials."


class IsModerator(RolePermission):
    allowed_roles = ("MODERATOR", "ADMIN")
    message = "This action is restricted to moderators."


class IsAdmin(RolePermission):
    allowed_roles = ("ADMIN",)
    message = "This action is restricted to administrators."


class IsVerifiedProfessional(permissions.BasePermission):
    """For actions that require a *verified* professional claim.

    Selecting a professional user type at signup is a statement of intent, not
    evidence -- verification is a separate, reviewed process (spec 6 and 28).
    """

    message = "This action requires a verified professional profile."

    def has_permission(self, request: Request, view: APIView) -> bool:
        user = request.user
        return bool(
            user and user.is_authenticated and getattr(user, "is_professionally_verified", False)
        )

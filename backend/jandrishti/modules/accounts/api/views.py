"""Account endpoints: the self view, onboarding, and public profiles."""

from __future__ import annotations

from django.db import transaction
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from jandrishti.modules.audit.application.recorder import record_audit
from jandrishti.shared.api.response import ok
from jandrishti.shared.api.views import ActorMixin

from ..domain.enums import UserRole
from ..models import ProfessionalProfile, User
from .serializers import (
    MeSerializer,
    ProfessionalProfileWriteSerializer,
    PublicUserSerializer,
    SelectUserTypeSerializer,
    UpdateProfileSerializer,
)


class MeView(ActorMixin, APIView):
    """GET/PATCH the signed-in account."""

    permission_classes = [IsAuthenticated]

    def get(self, request: Request) -> Response:
        return ok(MeSerializer(request.user).data)

    def patch(self, request: Request) -> Response:
        serializer = UpdateProfileSerializer(request.user, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return ok(MeSerializer(request.user).data)


class SelectUserTypeView(ActorMixin, APIView):
    """Onboarding: choose how you take part.

    Selecting PROFESSIONAL creates the profile shell but grants no badge. The
    badge comes only from a reviewed verification (spec 6, 28).
    """

    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def post(self, request: Request) -> Response:
        serializer = SelectUserTypeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        user: User = request.user

        previous_role = user.role
        user.role = data["role"]
        user.onboarding_completed = True
        user.save(update_fields=["role", "onboarding_completed", "updated_at"])

        if data["role"] == UserRole.PROFESSIONAL:
            ProfessionalProfile.objects.update_or_create(
                user=user,
                defaults={
                    "category": data.get("professional_category") or "OTHER",
                    "domain": data.get("domain") or "OTHER",
                },
            )

        record_audit(
            action="user.role_selected",
            actor=user,
            target=f"user:{user.id}",
            metadata={"from": previous_role, "to": user.role},
        )
        return ok(MeSerializer(user).data)


class ProfessionalProfileView(ActorMixin, APIView):
    """Create or update the signed-in user's professional profile."""

    permission_classes = [IsAuthenticated]

    def put(self, request: Request) -> Response:
        profile = getattr(request.user, "professional_profile", None)
        serializer = ProfessionalProfileWriteSerializer(
            profile, data=request.data, partial=profile is not None
        )
        serializer.is_valid(raise_exception=True)
        serializer.save(user=request.user)
        return ok(MeSerializer(request.user).data, status=status.HTTP_200_OK)


class PublicProfileView(APIView):
    """Anyone can read a public profile -- no login (spec 4)."""

    def get(self, request: Request, user_id: str) -> Response:
        user = get_object_or_404(
            User.objects.select_related("professional_profile").filter(is_active=True),
            pk=user_id,
        )
        return ok(PublicUserSerializer(user).data)

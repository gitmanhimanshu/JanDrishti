"""
Serializers are the API contract for accounts.

The split between `PublicUserSerializer` and `MeSerializer` is a privacy
boundary, not a convenience: email, role internals and onboarding state are
only ever returned to the account owner.
"""

from __future__ import annotations

from rest_framework import serializers

from ..domain.enums import ExpertiseDomain, ProfessionalCategory, UserRole
from ..models import ProfessionalProfile, User


class ProfessionalProfilePublicSerializer(serializers.Serializer):
    """Read-only projection driven by the profile privacy switches."""

    def to_representation(self, instance: ProfessionalProfile) -> dict:
        return instance.public_view()


class PublicUserSerializer(serializers.ModelSerializer):
    """The author card shown next to a problem, experience or comment."""

    id = serializers.UUIDField(read_only=True)
    professional_profile = serializers.SerializerMethodField()
    verification_badge = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            "id",
            "display_name",
            "avatar_url",
            "role",
            "is_professionally_verified",
            "verified_category",
            "verification_badge",
            "state",
            "professional_profile",
        ]
        read_only_fields = fields

    def get_professional_profile(self, obj: User) -> dict | None:
        profile = getattr(obj, "professional_profile", None)
        return profile.public_view() if profile else None

    def get_verification_badge(self, obj: User) -> str | None:
        """The badge asserts a verified claim -- not endorsement (spec 30)."""
        if not obj.is_professionally_verified:
            return None
        return {
            ProfessionalCategory.GOVERNMENT_EMPLOYEE: "Government Professional — Verified",
            ProfessionalCategory.RETIRED_GOVERNMENT_EMPLOYEE: (
                "Retired Government Professional — Verified"
            ),
            ProfessionalCategory.ARMED_FORCES: "Armed Forces Professional — Verified",
            ProfessionalCategory.RETIRED_ARMED_FORCES: (
                "Retired Armed Forces Professional — Verified"
            ),
            ProfessionalCategory.DOMAIN_EXPERT: "Domain Expert — Verified",
        }.get(obj.verified_category, "Professionally Verified")


class MeSerializer(serializers.ModelSerializer):
    """The full self view. Never used for anybody other than request.user."""

    id = serializers.UUIDField(read_only=True)
    professional_profile = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            "id",
            "email",
            "email_verified",
            "full_name",
            "display_name",
            "avatar_url",
            "role",
            "is_professionally_verified",
            "verified_category",
            "verified_at",
            "state",
            "city",
            "onboarding_completed",
            "is_banned",
            "created_at",
            "professional_profile",
        ]
        read_only_fields = [
            "id",
            "email",
            "email_verified",
            "role",
            "is_professionally_verified",
            "verified_category",
            "verified_at",
            "is_banned",
            "created_at",
        ]

    def get_professional_profile(self, obj: User) -> dict | None:
        profile = getattr(obj, "professional_profile", None)
        if not profile:
            return None
        # The owner sees their own private fields too.
        return {
            **profile.public_view(),
            "designation": profile.designation,
            "organization": profile.organization,
            "previous_organization": profile.previous_organization,
            "state": profile.state,
            "city": profile.city,
            "show_organization": profile.show_organization,
            "show_designation": profile.show_designation,
            "show_location": profile.show_location,
        }


class UpdateProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["full_name", "display_name", "state", "city"]

    def validate_display_name(self, value: str) -> str:
        value = value.strip()
        if value and len(value) < 2:
            raise serializers.ValidationError("Display name must be at least 2 characters.")
        return value


class SelectUserTypeSerializer(serializers.Serializer):
    """Onboarding step: pick CITIZEN or PROFESSIONAL.

    Elevated roles are absent from the choices on purpose -- a user cannot
    promote themselves to a moderator or a government official.
    """

    role = serializers.ChoiceField(choices=sorted(UserRole.self_selectable()))
    professional_category = serializers.ChoiceField(
        choices=ProfessionalCategory.choices, required=False, allow_blank=True
    )
    domain = serializers.ChoiceField(
        choices=ExpertiseDomain.choices, required=False, allow_blank=True
    )

    def validate(self, attrs: dict) -> dict:
        if attrs["role"] == UserRole.PROFESSIONAL and not attrs.get("professional_category"):
            raise serializers.ValidationError(
                {"professional_category": "Tell us which kind of professional you are."}
            )
        return attrs


class ProfessionalProfileWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProfessionalProfile
        fields = [
            "category",
            "domain",
            "headline",
            "bio",
            "designation",
            "organization",
            "previous_organization",
            "years_of_experience",
            "expertise_areas",
            "state",
            "city",
            "show_organization",
            "show_designation",
            "show_location",
        ]

    def validate_years_of_experience(self, value: int) -> int:
        if value > 80:
            raise serializers.ValidationError("That is more years than a working life.")
        return value

    def validate_expertise_areas(self, value: list) -> list:
        if not isinstance(value, list):
            raise serializers.ValidationError("Expertise areas must be a list.")
        if len(value) > 15:
            raise serializers.ValidationError("Please list at most 15 areas.")
        return [str(item).strip()[:60] for item in value if str(item).strip()]

"""Roles and professional categories.

Choosing a role at signup is a *declaration*. It grants nothing. Elevated roles
(GOVERNMENT_OFFICIAL, MODERATOR, ADMIN) are only ever assigned by an
administrator, and every such change lands in the audit log.
"""

from __future__ import annotations

from django.db import models


class UserRole(models.TextChoices):
    CITIZEN = "CITIZEN", "Citizen"
    PROFESSIONAL = "PROFESSIONAL", "Professional"
    GOVERNMENT_OFFICIAL = "GOVERNMENT_OFFICIAL", "Government official"
    MODERATOR = "MODERATOR", "Moderator"
    ADMIN = "ADMIN", "Administrator"

    @classmethod
    def self_selectable(cls) -> set[str]:
        """The only roles a user may pick for themselves during onboarding."""
        return {cls.CITIZEN.value, cls.PROFESSIONAL.value}

    @classmethod
    def staff_roles(cls) -> set[str]:
        return {cls.MODERATOR.value, cls.ADMIN.value}


class ProfessionalCategory(models.TextChoices):
    """What kind of experience someone brings.

    Deliberately not restricted to retirees: the platform values relevant
    experience over employment status (spec 3B).
    """

    WORKING_PROFESSIONAL = "WORKING_PROFESSIONAL", "Working professional"
    RETIRED_PROFESSIONAL = "RETIRED_PROFESSIONAL", "Retired professional"
    GOVERNMENT_EMPLOYEE = "GOVERNMENT_EMPLOYEE", "Government employee"
    RETIRED_GOVERNMENT_EMPLOYEE = "RETIRED_GOVERNMENT_EMPLOYEE", "Retired government employee"
    ARMED_FORCES = "ARMED_FORCES", "Armed forces"
    RETIRED_ARMED_FORCES = "RETIRED_ARMED_FORCES", "Retired armed forces"
    DOMAIN_EXPERT = "DOMAIN_EXPERT", "Domain expert"
    OTHER = "OTHER", "Other"


class ExpertiseDomain(models.TextChoices):
    INFRASTRUCTURE = "INFRASTRUCTURE", "Infrastructure"
    HEALTHCARE = "HEALTHCARE", "Healthcare"
    EDUCATION = "EDUCATION", "Education"
    ENVIRONMENT = "ENVIRONMENT", "Environment"
    WATER = "WATER", "Water and sanitation"
    ENERGY = "ENERGY", "Energy"
    TRANSPORT = "TRANSPORT", "Transport"
    PUBLIC_SAFETY = "PUBLIC_SAFETY", "Public safety"
    GOVERNANCE = "GOVERNANCE", "Governance and administration"
    LAW = "LAW", "Law"
    TECHNOLOGY = "TECHNOLOGY", "Technology"
    FINANCE = "FINANCE", "Finance"
    AGRICULTURE = "AGRICULTURE", "Agriculture"
    DISASTER_MANAGEMENT = "DISASTER_MANAGEMENT", "Disaster management"
    SOCIAL_WORK = "SOCIAL_WORK", "Social work"
    OTHER = "OTHER", "Other"

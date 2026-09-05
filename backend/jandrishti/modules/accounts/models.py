"""
Accounts: the one global JanDrishti identity (spec 7).

Identity design, and the reasons for it:

* `id` is an immutable UUID and is the only thing other tables reference. It is
  the primary identity: every foreign key in the platform points at it.
* Email is stored and is unique *when present* (Django requires uniqueness of
  the field it logs the admin in with), but it is explicitly not the identity.
  It is nullable, it can change when a user changes their Google account, and
  nothing joins on it -- so a changed address never strands a user's reports.
* `google_subject` (the OIDC `sub`) is the stable link to Google and is unique.
  It lives beside the account, not as the account: sign-in resolves an account
  through that column, never through email.
"""

from __future__ import annotations

import uuid

from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models
from django.utils import timezone

from jandrishti.shared.models import TimeStampedModel

from .domain.enums import ExpertiseDomain, ProfessionalCategory, UserRole


class UserManager(BaseUserManager):
    """Creation goes through Google OAuth; there is no password flow at all."""

    use_in_migrations = True

    def create_user(self, email: str = "", **extra) -> User:
        user = self.model(email=self.normalize_email(email) if email else None, **extra)
        user.set_unusable_password()
        user.save(using=self._db)
        return user

    def create_superuser(self, email: str, password: str | None = None, **extra) -> User:
        extra.setdefault("is_staff", True)
        extra.setdefault("is_superuser", True)
        extra.setdefault("role", UserRole.ADMIN)
        extra.setdefault("full_name", "Administrator")
        user = self.model(email=self.normalize_email(email), **extra)
        # Superusers are created by `createsuperuser` for the Django admin, so
        # this is the single place a password exists at all.
        user.set_password(password) if password else user.set_unusable_password()
        user.save(using=self._db)
        return user


class User(AbstractBaseUser, PermissionsMixin, TimeStampedModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # Nullable rather than blank: NULL repeats freely under a unique index,
    # so an account without an email is representable while two accounts can
    # never share one.
    email = models.EmailField(max_length=254, unique=True, null=True, blank=True)
    email_verified = models.BooleanField(default=False)
    full_name = models.CharField(max_length=150, blank=True)
    display_name = models.CharField(max_length=60, blank=True)
    avatar_url = models.URLField(max_length=500, blank=True)

    role = models.CharField(
        max_length=32, choices=UserRole.choices, default=UserRole.CITIZEN, db_index=True
    )

    # Denormalised from the professional_verification module so that rendering a
    # badge on a list of 50 comments is one query, not fifty. The verification
    # module owns the write; this is a read-through cache with an audited source.
    is_professionally_verified = models.BooleanField(default=False, db_index=True)
    verified_category = models.CharField(
        max_length=40, choices=ProfessionalCategory.choices, blank=True
    )
    verified_at = models.DateTimeField(null=True, blank=True)

    # Public, coarse location. Never an address.
    state = models.CharField(max_length=120, blank=True, db_index=True)
    city = models.CharField(max_length=120, blank=True)

    onboarding_completed = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    is_banned = models.BooleanField(default=False)
    banned_reason = models.CharField(max_length=300, blank=True)
    last_seen_at = models.DateTimeField(null=True, blank=True)

    objects = UserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS: list[str] = []

    class Meta:
        db_table = "accounts_user"
        indexes = [
            models.Index(fields=["role", "is_active"]),
            models.Index(fields=["is_professionally_verified", "verified_category"]),
        ]

    def __str__(self) -> str:
        return self.display_name or self.full_name or self.email or str(self.id)

    def save(self, *args, **kwargs):
        # Empty string would collide under the unique index; NULL does not.
        if not self.email:
            self.email = None
        if not self.display_name:
            local_part = self.email.split("@")[0] if self.email else ""
            self.display_name = (self.full_name or local_part or "Citizen")[:60]
        super().save(*args, **kwargs)

    # -- domain queries the rest of the platform asks of a user ---------------

    @property
    def is_staff_role(self) -> bool:
        return self.role in UserRole.staff_roles() or self.is_superuser

    @property
    def is_government(self) -> bool:
        return self.role == UserRole.GOVERNMENT_OFFICIAL or self.is_superuser

    @property
    def can_interact(self) -> bool:
        """Banned accounts keep read access; they lose the ability to write."""
        return self.is_active and not self.is_banned

    def touch_last_seen(self) -> None:
        now = timezone.now()
        # Coarse to the minute: this fires on every authenticated request and is
        # not worth a write per request.
        if not self.last_seen_at or (now - self.last_seen_at).total_seconds() > 300:
            User.objects.filter(pk=self.pk).update(last_seen_at=now)


class GoogleIdentity(TimeStampedModel):
    """The Google link, kept separate from the account it authenticates.

    Section 6: Google proves control of a Google account and nothing else. No
    professional claim is ever derived from anything in this table.
    """

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="google_identity")
    google_subject = models.CharField(max_length=255, unique=True, db_index=True)
    email_at_link = models.EmailField(max_length=254, blank=True)
    picture_url = models.URLField(max_length=500, blank=True)
    last_login_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "accounts_google_identity"

    def __str__(self) -> str:
        return f"google:{self.google_subject[:12]}…"


class ProfessionalProfile(TimeStampedModel):
    """Optional public professional context for a user.

    Everything here is self-asserted until the verification module says
    otherwise, and only the fields the user marks public are ever serialised
    into a public response.
    """

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="professional_profile")
    category = models.CharField(
        max_length=40, choices=ProfessionalCategory.choices, default=ProfessionalCategory.OTHER
    )
    domain = models.CharField(
        max_length=40, choices=ExpertiseDomain.choices, default=ExpertiseDomain.OTHER, db_index=True
    )
    headline = models.CharField(max_length=160, blank=True)
    bio = models.TextField(max_length=2000, blank=True)
    designation = models.CharField(max_length=150, blank=True)
    organization = models.CharField(max_length=200, blank=True)
    previous_organization = models.CharField(max_length=200, blank=True)
    years_of_experience = models.PositiveSmallIntegerField(default=0)
    expertise_areas = models.JSONField(default=list, blank=True)
    state = models.CharField(max_length=120, blank=True, db_index=True)
    city = models.CharField(max_length=120, blank=True)

    # Privacy switches. Default to the least revealing option (spec 27, 68).
    show_organization = models.BooleanField(default=False)
    show_designation = models.BooleanField(default=True)
    show_location = models.BooleanField(default=True)

    class Meta:
        db_table = "accounts_professional_profile"
        indexes = [models.Index(fields=["domain", "category"])]

    def __str__(self) -> str:
        return f"{self.user} — {self.get_category_display()}"

    def public_view(self) -> dict:
        """Exactly the subset the user has agreed to publish."""
        data = {
            "category": self.category,
            "category_display": self.get_category_display(),
            "domain": self.domain,
            "domain_display": self.get_domain_display(),
            "headline": self.headline,
            "bio": self.bio,
            "years_of_experience": self.years_of_experience,
            "expertise_areas": self.expertise_areas or [],
        }
        if self.show_designation:
            data["designation"] = self.designation
        if self.show_organization:
            data["organization"] = self.organization
        if self.show_location:
            data["state"] = self.state
            data["city"] = self.city
        return data

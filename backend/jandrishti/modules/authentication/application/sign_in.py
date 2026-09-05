"""
Sign-in use cases.

The whole of section 6 lives here: Google establishes an identity, JanDrishti
mints its own session, and nothing about a profession is inferred along the way.
There is no password path and no OTP step to write, because neither exists.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

from django.db import transaction
from django.utils import timezone

from jandrishti.modules.accounts.models import GoogleIdentity, User
from jandrishti.modules.audit.application.recorder import record_audit
from jandrishti.shared.application.use_case import Actor, UseCase
from jandrishti.shared.domain.exceptions import PermissionDeniedError, ValidationError

from ..domain.ports import ExternalIdentity, IdentityProvider
from ..infrastructure.tokens import JWTTokenService
from ..models import RefreshToken

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class SignInWithGoogleCommand:
    code: str = ""
    id_token: str = ""
    redirect_uri: str | None = None
    actor: Actor = None  # type: ignore[assignment]


@dataclass(slots=True)
class SessionResult:
    user: User
    access_token: str
    access_expires_in: int
    refresh_token: str
    is_new_user: bool


class SignInWithGoogleUseCase(UseCase[SignInWithGoogleCommand, SessionResult]):
    def __init__(
        self,
        identity_provider: IdentityProvider,
        token_service: JWTTokenService | None = None,
        event_bus=None,
    ) -> None:
        super().__init__(event_bus)
        self._provider = identity_provider
        self._tokens = token_service or JWTTokenService()

    def handle(self, request: SignInWithGoogleCommand) -> SessionResult:
        if not (request.code or request.id_token):
            raise ValidationError("Provide either an authorization code or an ID token.")

        identity = (
            self._provider.verify_id_token(request.id_token)
            if request.id_token
            else self._provider.exchange_code(request.code, request.redirect_uri)
        )

        user, is_new = self._resolve_user(identity)

        if user.is_banned:
            raise PermissionDeniedError("This account has been suspended.")
        if not user.is_active:
            raise PermissionDeniedError("This account is not active.")

        access_token, expires_in = self._tokens.issue_access_token(str(user.id), user.role)
        actor = request.actor or Actor.anonymous()
        raw_refresh, _row = RefreshToken.issue(
            user, user_agent=actor.user_agent, ip_address=actor.ip_address or None
        )

        record_audit(
            action="auth.signed_in",
            actor=user,
            target=f"user:{user.id}",
            metadata={"provider": identity.provider, "new_account": is_new},
            ip_address=actor.ip_address or None,
            request_id=actor.request_id,
        )
        return SessionResult(
            user=user,
            access_token=access_token,
            access_expires_in=expires_in,
            refresh_token=raw_refresh,
            is_new_user=is_new,
        )

    @transaction.atomic
    def _resolve_user(self, identity: ExternalIdentity) -> tuple[User, bool]:
        """Find or create the global account behind this Google subject.

        The lookup is by `google_subject` and never by email: matching on email
        would let anyone who acquires a recycled address inherit an existing
        account, and it would break for users who change their Google email.
        """
        link = (
            GoogleIdentity.objects.select_related("user")
            .filter(google_subject=identity.subject)
            .first()
        )
        if link:
            link.last_login_at = timezone.now()
            link.save(update_fields=["last_login_at", "updated_at"])
            user = link.user
            # Keep the display picture fresh, but never overwrite a name the
            # user has edited themselves.
            updates: list[str] = []
            if identity.picture_url and user.avatar_url != identity.picture_url:
                user.avatar_url = identity.picture_url
                updates.append("avatar_url")
            if updates:
                user.save(update_fields=[*updates, "updated_at"])
            return user, False

        user = User.objects.create_user(
            email=identity.email,
            email_verified=identity.email_verified,
            full_name=identity.full_name,
            avatar_url=identity.picture_url,
        )
        GoogleIdentity.objects.create(
            user=user,
            google_subject=identity.subject,
            email_at_link=identity.email,
            picture_url=identity.picture_url,
            last_login_at=timezone.now(),
        )
        return user, True


@dataclass(slots=True)
class RefreshSessionCommand:
    refresh_token: str
    actor: Actor = None  # type: ignore[assignment]


class RefreshSessionUseCase(UseCase[RefreshSessionCommand, SessionResult]):
    """Rotates the refresh token and detects replay.

    Presenting an already-rotated token means either a race or a stolen token.
    We cannot tell which, so we assume the worse case and revoke the family --
    the legitimate user signs in again, the attacker gets nothing.
    """

    def __init__(self, token_service: JWTTokenService | None = None, event_bus=None) -> None:
        super().__init__(event_bus)
        self._tokens = token_service or JWTTokenService()

    def handle(self, request: RefreshSessionCommand) -> SessionResult:
        from ..models import hash_token

        row = (
            RefreshToken.objects.select_related("user")
            .filter(token_hash=hash_token(request.refresh_token))
            .first()
        )
        if row is None:
            raise ValidationError("Invalid session. Please sign in again.")

        if not row.is_active:
            revoked = RefreshToken.revoke_family(row.family)
            logger.warning("refresh token replay detected", extra={"revoked_tokens": revoked})
            record_audit(
                action="auth.refresh_replay_detected",
                actor=row.user,
                target=f"user:{row.user_id}",
                metadata={"revoked_tokens": revoked},
            )
            raise ValidationError("This session is no longer valid. Please sign in again.")

        user = row.user
        if not user.can_interact:
            raise PermissionDeniedError("This account has been suspended.")

        actor = request.actor or Actor.anonymous()
        raw_refresh, new_row = RefreshToken.issue(
            user,
            family=row.family,
            user_agent=actor.user_agent,
            ip_address=actor.ip_address or None,
        )
        row.revoke(replaced_by=new_row.token_hash)

        access_token, expires_in = self._tokens.issue_access_token(str(user.id), user.role)
        return SessionResult(
            user=user,
            access_token=access_token,
            access_expires_in=expires_in,
            refresh_token=raw_refresh,
            is_new_user=False,
        )


@dataclass(slots=True)
class SignOutCommand:
    refresh_token: str = ""
    all_sessions: bool = False
    actor: Actor = None  # type: ignore[assignment]


class SignOutUseCase(UseCase[SignOutCommand, None]):
    def handle(self, request: SignOutCommand) -> None:
        from ..models import hash_token

        actor = request.actor or Actor.anonymous()
        if request.all_sessions and actor.is_authenticated:
            RefreshToken.objects.filter(user=actor.user, revoked_at__isnull=True).update(
                revoked_at=timezone.now()
            )
            return None

        if request.refresh_token:
            row = RefreshToken.objects.filter(
                token_hash=hash_token(request.refresh_token), revoked_at__isnull=True
            ).first()
            if row:
                row.revoke()
        return None

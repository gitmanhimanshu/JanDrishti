"""
DRF authentication class.

Presenting a valid token identifies you. It does not authorize you: the role
used for every permission check is read from the database row, not from the
token, so a role revoked a minute ago takes effect on the next request.
"""

from __future__ import annotations

from rest_framework.authentication import BaseAuthentication, get_authorization_header
from rest_framework.exceptions import AuthenticationFailed
from rest_framework.request import Request

from jandrishti.modules.accounts.models import User
from jandrishti.shared.domain.exceptions import AuthenticationRequiredError

from ..infrastructure.tokens import JWTTokenService


class JWTAuthentication(BaseAuthentication):
    keyword = b"bearer"

    def __init__(self) -> None:
        self._tokens = JWTTokenService()

    def authenticate(self, request: Request) -> tuple[User, str] | None:
        header = get_authorization_header(request).split()
        if not header or header[0].lower() != self.keyword:
            # No credentials at all is the normal case on this platform: the
            # request continues as anonymous and public content is served.
            return None
        if len(header) != 2:
            raise AuthenticationFailed("Malformed Authorization header.")

        raw_token = header[1].decode("utf-8", errors="ignore")
        try:
            claims = self._tokens.decode_access_token(raw_token)
        except AuthenticationRequiredError as exc:
            raise AuthenticationFailed(exc.message) from exc

        user = User.objects.filter(pk=claims["sub"], is_active=True).first()
        if user is None:
            raise AuthenticationFailed("Account not found.")
        if user.is_banned:
            raise AuthenticationFailed("This account has been suspended.")

        user.touch_last_seen()
        return user, raw_token

    def authenticate_header(self, request: Request) -> str:
        return 'Bearer realm="api"'

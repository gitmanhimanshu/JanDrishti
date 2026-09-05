"""JWT access tokens.

Short TTL and no revocation list: an access token is a 30-minute bearer of a
user id, and anything longer-lived is the refresh token, which *is* revocable.
The role is embedded only as a hint for the client UI -- the server always
re-reads the role from the database before authorizing anything.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

import jwt
from django.conf import settings

from jandrishti.shared.domain.exceptions import AuthenticationRequiredError

TOKEN_TYPE_ACCESS = "access"  # noqa: S105 - a token *type*, not a token


class JWTTokenService:
    def __init__(self, secret: str | None = None) -> None:
        self._secret = secret or settings.SECRET_KEY
        self._algorithm = settings.JWT_ALGORITHM
        self._issuer = settings.JWT_ISSUER

    def issue_access_token(self, user_id: str, role: str) -> tuple[str, int]:
        now = datetime.now(UTC)
        expires = now + settings.JWT_ACCESS_TTL
        payload = {
            "sub": str(user_id),
            "role": role,
            "typ": TOKEN_TYPE_ACCESS,
            "iss": self._issuer,
            "iat": int(now.timestamp()),
            "exp": int(expires.timestamp()),
            "jti": uuid.uuid4().hex,
        }
        token = jwt.encode(payload, self._secret, algorithm=self._algorithm)
        return token, int(settings.JWT_ACCESS_TTL.total_seconds())

    def decode_access_token(self, token: str) -> dict:
        try:
            claims = jwt.decode(
                token,
                self._secret,
                algorithms=[self._algorithm],
                issuer=self._issuer,
                options={"require": ["exp", "sub", "iss"]},
            )
        except jwt.ExpiredSignatureError as exc:
            raise AuthenticationRequiredError(
                "Your session has expired. Please sign in again."
            ) from exc
        except jwt.InvalidTokenError as exc:
            raise AuthenticationRequiredError("Invalid authentication token.") from exc

        if claims.get("typ") != TOKEN_TYPE_ACCESS:
            raise AuthenticationRequiredError("Wrong token type.")
        return claims

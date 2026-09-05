"""
Google OAuth adapter.

The only file in the codebase that knows Google exists. It implements the
`IdentityProvider` port and returns a provider-neutral `ExternalIdentity`.

Two entry paths are supported because real clients use both:
* authorization code exchange (server-side redirect flow), and
* direct ID token verification (Google Identity Services button on the web app).
"""

from __future__ import annotations

import logging
from urllib.parse import urlencode

import requests
from django.conf import settings
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token as google_id_token

from jandrishti.shared.domain.exceptions import ExternalServiceError, ValidationError

from ..domain.ports import ExternalIdentity

logger = logging.getLogger(__name__)

GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"  # noqa: S105 - a URL, not a secret
ACCEPTED_ISSUERS = {"accounts.google.com", "https://accounts.google.com"}


class GoogleIdentityProvider:
    def __init__(
        self,
        client_id: str | None = None,
        client_secret: str | None = None,
        redirect_uri: str | None = None,
        timeout: int = 10,
    ) -> None:
        self._client_id = client_id or settings.GOOGLE_CLIENT_ID
        self._client_secret = client_secret or settings.GOOGLE_CLIENT_SECRET
        self._redirect_uri = redirect_uri or settings.GOOGLE_REDIRECT_URI
        self._timeout = timeout

    def _require_config(self) -> None:
        if not self._client_id:
            raise ExternalServiceError("Google sign-in is not configured on this server.")

    def authorization_url(self, state: str, redirect_uri: str | None = None) -> str:
        self._require_config()
        params = {
            "client_id": self._client_id,
            "redirect_uri": redirect_uri or self._redirect_uri,
            "response_type": "code",
            "scope": "openid email profile",
            "state": state,
            "access_type": "online",
            "prompt": "select_account",
            "include_granted_scopes": "true",
        }
        return f"{GOOGLE_AUTH_URL}?{urlencode(params)}"

    def exchange_code(self, code: str, redirect_uri: str | None = None) -> ExternalIdentity:
        self._require_config()
        if not self._client_secret:
            raise ExternalServiceError("Google sign-in is not fully configured on this server.")
        try:
            response = requests.post(
                GOOGLE_TOKEN_URL,
                data={
                    "code": code,
                    "client_id": self._client_id,
                    "client_secret": self._client_secret,
                    "redirect_uri": redirect_uri or self._redirect_uri,
                    "grant_type": "authorization_code",
                },
                timeout=self._timeout,
            )
        except requests.RequestException as exc:
            logger.warning("google token endpoint unreachable")
            raise ExternalServiceError("Could not reach Google. Please try again.") from exc

        if response.status_code != 200:
            # Deliberately vague to the caller: the detail is a Google error
            # body that may echo the code back.
            logger.warning("google code exchange failed", extra={"status": response.status_code})
            raise ValidationError("That Google sign-in could not be completed. Please try again.")

        raw_id_token = response.json().get("id_token")
        if not raw_id_token:
            raise ExternalServiceError("Google did not return an identity token.")
        return self.verify_id_token(raw_id_token)

    def verify_id_token(self, id_token: str) -> ExternalIdentity:
        """Verify signature, audience, issuer and expiry via Google certificates."""
        self._require_config()
        try:
            claims = google_id_token.verify_oauth2_token(
                id_token, google_requests.Request(), self._client_id
            )
        except ValueError as exc:
            logger.info("rejected google id token")
            raise ValidationError("This Google sign-in could not be verified.") from exc

        if claims.get("iss") not in ACCEPTED_ISSUERS:
            raise ValidationError("Unexpected token issuer.")
        subject = claims.get("sub")
        if not subject:
            raise ValidationError("Google token is missing a subject identifier.")

        return ExternalIdentity(
            subject=subject,
            email=claims.get("email", ""),
            email_verified=bool(claims.get("email_verified", False)),
            full_name=claims.get("name", "") or claims.get("given_name", ""),
            picture_url=claims.get("picture", ""),
            provider="google",
        )

"""
Ports for authentication.

The use case depends on `IdentityProvider`, not on Google. That is what makes
it possible to add a second provider later, and what makes the sign-in flow
testable without ever contacting Google.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, runtime_checkable


@dataclass(frozen=True, slots=True)
class ExternalIdentity:
    """What an identity provider actually proves: control of an account.

    Nothing here is evidence of a profession, an employer or a rank. Those
    claims go through professional_verification (spec 6).
    """

    subject: str
    email: str = ""
    email_verified: bool = False
    full_name: str = ""
    picture_url: str = ""
    provider: str = "google"


@runtime_checkable
class IdentityProvider(Protocol):
    def authorization_url(self, state: str, redirect_uri: str | None = None) -> str: ...

    def exchange_code(self, code: str, redirect_uri: str | None = None) -> ExternalIdentity: ...

    def verify_id_token(self, id_token: str) -> ExternalIdentity: ...


@runtime_checkable
class TokenService(Protocol):
    def issue_access_token(self, user_id: str, role: str) -> tuple[str, int]: ...

    def decode_access_token(self, token: str) -> dict: ...

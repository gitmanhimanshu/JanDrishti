"""
The payment gateway port, and the deliberately inert default adapter.

`PaymentGateway` is what the application layer depends on. `DisabledPaymentGateway`
is what it gets until a real provider is configured *and* the legal structure in
docs/decisions/funding.md is in place -- it refuses every charge rather than
pretending to take money.

This is not a stub left unfinished. It is the safe default: the spec is explicit
that real-money collection must not launch without the surrounding architecture,
and an adapter that raises is the honest way to encode that.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Protocol, runtime_checkable

from django.conf import settings

from jandrishti.shared.domain.exceptions import FeatureDisabledError


@dataclass(frozen=True, slots=True)
class PaymentIntent:
    reference: str
    provider: str
    amount: Decimal
    currency: str
    checkout_url: str = ""
    client_secret: str = ""


@dataclass(frozen=True, slots=True)
class PaymentResult:
    reference: str
    succeeded: bool
    settled_amount: Decimal
    failure_reason: str = ""


@runtime_checkable
class PaymentGateway(Protocol):
    name: str

    def create_intent(
        self, *, amount: Decimal, currency: str, idempotency_key: str, metadata: dict
    ) -> PaymentIntent: ...

    def verify_callback(self, payload: dict, signature: str) -> PaymentResult: ...

    def refund(self, reference: str, amount: Decimal) -> PaymentResult: ...


class DisabledPaymentGateway:
    """The default. Every money-moving call fails loudly."""

    name = "disabled"

    _MESSAGE = (
        "Community funding is not accepting contributions on this deployment. "
        "Real-money collection requires a regulated payment provider, a legal "
        "entity to hold the funds, and a refund and dispute process."
    )

    def create_intent(self, **kwargs) -> PaymentIntent:
        raise FeatureDisabledError(self._MESSAGE)

    def verify_callback(self, payload: dict, signature: str) -> PaymentResult:
        raise FeatureDisabledError(self._MESSAGE)

    def refund(self, reference: str, amount: Decimal) -> PaymentResult:
        raise FeatureDisabledError(self._MESSAGE)


def get_payment_gateway() -> PaymentGateway:
    """Adapter selection.

    When a provider is integrated, it is registered here and nothing in the
    application layer changes.
    """
    if not settings.FUNDING_PAYMENTS_ENABLED:
        return DisabledPaymentGateway()
    raise FeatureDisabledError(
        "FUNDING_PAYMENTS_ENABLED is set, but no payment provider adapter is registered. "
        "Register one in jandrishti/modules/funding/domain/gateway.py before enabling payments."
    )

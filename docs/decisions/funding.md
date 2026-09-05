# Community funding ships disabled

**Status:** accepted — payments off by default

## Decision

The funding schema, the transparency model and the gateway port are built. The
default gateway adapter refuses every charge, and `FUNDING_PAYMENTS_ENABLED`
defaults to false.

This is the finished state of this module for now, not an unfinished one.

## Why

Collecting money from the public is not a payments integration. It is a legal
undertaking. Before a single rupee moves, all of the following must exist:

- **A legal entity** to receive funds. Community money must never route into a
  personal bank account — the schema records `legal_entity_name` and
  `legal_entity_registration` on the campaign for exactly this reason.
- **A regulated payment provider**, with the compliance obligations that come
  with it.
- **Escrow or a segregated account** where the structure calls for it, so
  contributions are not commingled with operating funds.
- **KYC/AML** where thresholds apply.
- **A refund and dispute process** that actually works. The spec is explicit:
  do not promise automatic refunds unless the architecture supports them.
- **Financial auditability** — every rupee in traceable to a contribution, every
  rupee out traceable to an evidenced expense.

Shipping a working payment button before these exist would be the most harmful
thing this codebase could do. A citizen who contributes to a road repair and
cannot get their money back has been wronged in a way no amount of good
intention repairs.

## What is built

**Schema.** `FundingCampaign`, `Contribution`, `Expense`, plus expense evidence
through the shared media attachment table. Check constraints keep amounts
positive and totals non-negative. Contributions carry a unique
`idempotency_key`, so a retried provider callback cannot create a second
payment.

**Transparency model.** The four numbers the public is owed — target, collected,
spent, remaining — are exposed on every campaign, alongside itemised expenses
with vendor, date, invoice number, receipt and verification status.

**The port.**

```python
class PaymentGateway(Protocol):
    def create_intent(self, *, amount, currency, idempotency_key, metadata) -> PaymentIntent: ...
    def verify_callback(self, payload: dict, signature: str) -> PaymentResult: ...
    def refund(self, reference: str, amount: Decimal) -> PaymentResult: ...
```

**The default adapter.** `DisabledPaymentGateway` raises `FeatureDisabledError`
on every money-moving call. The API returns a 503 with a plain explanation
rather than a checkout flow that does nothing.

No card, bank or UPI detail is stored anywhere in this schema. That is the
payment provider's obligation, and their compliance burden.

## Turning it on

1. Establish the legal entity and the account structure.
2. Integrate a regulated provider: implement `PaymentGateway`, register it in
   `get_payment_gateway()`.
3. Implement webhook signature verification and idempotent settlement.
4. Implement refunds against the real provider semantics.
5. Add reconciliation between provider settlements and `Contribution` rows.
6. Only then set `FUNDING_PAYMENTS_ENABLED=True`.

Setting the flag without step 2 raises at startup with an explicit message,
rather than silently falling back to something that appears to work.

## Consequences

The funding module is visibly incomplete to a reader, and deliberately so. The
alternative — a working-looking payment path without the surrounding structure
— would be worse than an honest refusal.

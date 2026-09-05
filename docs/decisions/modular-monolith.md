# Modular monolith, not microservices

**Status:** accepted

## Context

The platform must credibly reach 10M+ users. That target invites a
microservices architecture from day one.

## Decision

One deployable Django application, divided into modules with enforced
boundaries. Extraction later, when a specific requirement justifies it.

## Why

Microservices trade a local problem (organising code) for distributed ones
(network partitions, partial failure, distributed transactions, versioned
contracts, tracing across hops, N deployment pipelines). Those costs are paid
from the first day; the benefits arrive only when independent scaling or
independent ownership is actually needed.

Concretely, the hard parts of this platform are not solved by splitting:

- **Support counting.** A unique constraint plus an atomic increment in one
  transaction is correct under any load. Split across services it becomes a
  distributed transaction or an eventually-consistent count that citizens will
  see disagree with itself.
- **Issue clustering.** Needs to query problems by location, category and time.
  In one database this is an indexed query; across services it is a fan-out
  with pagination and partial failure.
- **The government dashboard.** Joins problems, departments, memberships and
  assignments. One query here, an orchestration layer there.

## What keeps this honest

A modular monolith degrades into a big ball of mud unless the boundaries are
real. Ours are:

- Each module has its own `domain/`, `application/`, `infrastructure/`, `api/`.
- A module never queries another module's models directly. Cross-module reads
  go through application services; cross-module reactions go through domain
  events.
- Modules communicate about facts (`ProblemCreated`), not commands.

The clearest evidence this holds: `problems` does not import `notifications`.
It publishes an event. Deleting every notification handler would leave the
platform working, just quieter.

## Extraction path

Already-drawn seams, in the order they would be taken:
`authentication` → `notifications` → `search` → `media processing` →
`analytics`. Each has few inbound dependencies and a clear contract.

The trigger is a real requirement — traffic needing independent scaling,
deployment cadence needing independence, separate team ownership, or failure
isolation that genuinely matters — not a growth milestone.

## Consequences

Good: one deploy, one database, real transactions, no distributed debugging,
fast tests, straightforward local development.

Bad: everything scales together; a memory leak affects all modules; discipline
about boundaries has to be maintained by review, since the compiler will not
enforce it.

Accepted, because the second list is cheaper to live with than the first
alternative until traffic says otherwise.

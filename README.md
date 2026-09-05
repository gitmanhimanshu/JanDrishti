# JanDrishti

**See. Suggest. Solve.**

A public-first civic intelligence platform. Citizens report public problems with
evidence; experienced professionals explain root causes and recommend action;
departments act; and the whole record — including the proof, or its absence —
stays public.

*Jan* = people. *Drishti* = perspective.

```
Problem → Evidence → Experience → Recommendation → Action → Proof → Impact
```

## Quick start

```bash
docker compose up --build
```

Frontend on <http://localhost:3000>, API on <http://localhost:8000>, docs at
<http://localhost:8000/api/docs/>.

Without Docker, see [docs/development.md](docs/development.md). The backend runs
on SQLite with no external services if `DATABASE_URL` and `REDIS_URL` are unset,
so a fresh clone works immediately.

## What is here

```
backend/     Django + DRF, modular monolith, clean architecture
frontend/    Next.js 15 App Router, TypeScript, Tailwind
docs/        Architecture, database, API, security, scalability, decisions
```

**Backend** — 19 modules, each with `domain/`, `application/`,
`infrastructure/` and `api/` layers. 160 tests. Ruff-clean.

**Frontend** — server-rendered public pages, feature-organised, typed against
the API contract, accessible by construction.

## The commitments this codebase keeps

**Anyone can read everything, without an account.** Problems, evidence,
experiences, projects, progress, funding. Signing in is only for taking part —
and the login prompt appears *after* you act, then completes what you were doing.

**Google OAuth only.** No passwords, no OTP. Google proves control of a Google
account and nothing more.

**Authentication is not verification.** A professional badge comes from a
reviewed document, decided by a person, written in exactly one place in the
codebase.

**Uploaded is not verified.** The interface says "Uploaded, not verified" in
plain words. Nothing automated can mark evidence verified.

**Support is a signal, not proof.** Experience ranking blends verification,
relevance, evidence quality and how actionable a recommendation is. Popularity
is a small input, and there is a test asserting a thorough quiet contribution
outranks a popular empty one.

**500 reports of one pothole become one work item and stay 500 reports.**
Clustering aggregates for the department without destroying anything — every
original keeps its author, evidence and timeline.

**Counters cannot drift.** A unique constraint is the truth; the cached column
moves atomically in the same transaction. A thousand simultaneous supporters
produce exactly a thousand rows.

**Aadhaar is never stored as a number.** There is no field for it, and a test
asserts that against the model definition. Optional fallback only, never a
login, never public, redacted from logs by pattern.

**Money stays off until it is safe.** The funding schema and gateway port exist;
the default adapter refuses every charge. See
[docs/decisions/funding.md](docs/decisions/funding.md).

**Statistics are never invented.** A new deployment shows zeros and honest empty
states.

## Architecture in one diagram

```
Presentation  api/            DRF views, serializers, permissions, throttles
     │
Application   application/    use cases, transactions, events
     │
Domain        domain/         entities, value objects, state machines, scoring
     ↑
Infrastructure infrastructure/ ORM, Cloudinary, Google, Redis — implements the ports
```

The dependency rule points inwards. Domain code imports no framework, which is
why the entire problem lifecycle, ranking and clustering logic is unit-testable
in about a second.

Full detail: [docs/architecture.md](docs/architecture.md).

## Tests

```bash
cd backend && pytest        # 160 passed
```

| Suite | What it protects |
| --- | --- |
| `test_domain.py` | Lifecycle legality, ranking, clustering scores, credibility weights |
| `test_api_public_access.py` | Anonymous reads work; every write is gated |
| `test_problems.py` | Routing, support concurrency, transition authorization |
| `test_experience_and_social.py` | Publishing, comment nesting caps, cross-thread replies |
| `test_clustering.py` | Merging aggregates without destroying originals |
| `test_security.py` | Escalation, IDOR, forged tokens, upload confusion, Aadhaar, redaction |

## Documentation

| Document | Contents |
| --- | --- |
| [architecture.md](docs/architecture.md) | System diagram, layers, modules, events |
| [database.md](docs/database.md) | ER design, counters under concurrency, indexes |
| [api.md](docs/api.md) | Endpoints, envelope, error codes, rate limits |
| [security.md](docs/security.md) | Auth, authorization, Aadhaar, documents, uploads |
| [scalability.md](docs/scalability.md) | 100K → 1M → 10M+, and the seams already in place |
| [deployment.md](docs/deployment.md) | Environment, release, processes, backups |
| [development.md](docs/development.md) | Local setup, tests, where code belongs |
| [decisions/](docs/decisions/) | Why modular monolith, PostgreSQL, no Kafka, no Elasticsearch, funding off |

## Stack

Django 5.1 · DRF · PostgreSQL · Redis · Celery · Cloudinary ·
Next.js 15 · TypeScript · Tailwind

## Engineering principle

> Simple where possible. Strong where necessary. Scalable by design.

No technology is here because it is fashionable. Each earns its place by solving
a problem this platform actually has — and the ones deliberately left out are
documented with the trigger that would bring them in.

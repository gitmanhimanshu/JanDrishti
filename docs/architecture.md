# Architecture

## System

```
                        Citizens, professionals, officials
                                      │
                        ┌─────────────┴─────────────┐
                        │      CDN / edge cache      │   public pages are cacheable
                        └─────────────┬─────────────┘
                                      │
                        ┌─────────────┴─────────────┐
                        │   Next.js (App Router)     │   SSR for public content, SEO
                        └─────────────┬─────────────┘
                                      │ REST /api/v1
                        ┌─────────────┴─────────────┐
                        │      Load balancer         │
                        └─────────────┬─────────────┘
                                      │
                        ┌─────────────┴─────────────┐
                        │   Django + DRF instances   │   stateless; scale horizontally
                        │  ┌──────────────────────┐  │
                        │  │  Presentation (api)  │  │
                        │  │  Application         │  │
                        │  │  Domain              │  │
                        │  │  Infrastructure      │  │
                        │  └──────────────────────┘  │
                        └───┬────────┬───────┬───────┘
                            │        │       │
            ┌───────────────┘        │       └────────────────┐
            │                        │                        │
    ┌───────┴───────┐     ┌──────────┴────────┐     ┌─────────┴────────┐
    │  PostgreSQL   │     │       Redis       │     │    Cloudinary    │
    │ source of     │     │ cache, throttles, │     │  media bytes     │
    │ truth         │     │ locks, broker     │     │                  │
    └───────────────┘     └──────────┬────────┘     └──────────────────┘
                                     │
                          ┌──────────┴────────┐
                          │  Celery workers   │  clustering, notifications,
                          │  + beat           │  media, analytics, retention
                          └───────────────────┘
```

### Why each component

| Component | Why it is here | What breaks without it |
| --- | --- | --- |
| **Next.js** | Public pages must be readable without an account and indexable by search engines. Server rendering gives both. | Anonymous browsing becomes a blank page with a spinner; shared links show nothing. |
| **Django + DRF** | Mature ORM, migrations, admin, permissions and a large, auditable security surface. The domain logic is plain Python and does not depend on Django. | — |
| **PostgreSQL** | Every count on the platform must be reconstructible from rows. Needs real constraints, partial indexes, full-text search and transactions. | Support counts drift; duplicate supports become possible. |
| **Redis** | Cache, rate limiting, the Celery broker, and the one distributed lock that clustering needs. Never a source of truth. | Slower, and rate limiting becomes per-process. Nothing is lost. |
| **Celery** | Duplicate detection scores up to 200 candidates; nobody should wait on that while pressing Submit. | Submissions get slow and time out under load. |
| **Cloudinary** | Media bytes do not belong in PostgreSQL. Private assets get signed, expiring URLs. | Falls back to the local filesystem adapter, which works but does not scale across instances. |

## Layers

The dependency rule points inwards. Domain code imports nothing from the layers
outside it.

```
Presentation  (jandrishti/modules/*/api/)
    serializers, views, permissions, throttles
    knows: HTTP, DRF                         →  calls Application
        │
Application   (jandrishti/modules/*/application/)
    use cases, orchestration, transactions, events
    knows: repositories and ports            →  calls Domain
        │
Domain        (jandrishti/modules/*/domain/)
    entities, value objects, state machines, ranking strategies, scoring
    knows: nothing outside itself
        ↑
Infrastructure (jandrishti/modules/*/infrastructure/)
    Django ORM, Cloudinary, Google, Redis, payment adapters
    implements the ports the inner layers declare
```

### The rule in practice

`SupportProblemUseCase` needs to know whether a person already supports a
problem. It does not ask Redis, and it does not read a counter. It inserts a
row and lets the unique constraint answer:

```python
try:
    with transaction.atomic():
        ProblemSupport.objects.create(problem=problem, user=user)
        Problem.objects.filter(pk=problem.pk).update(support_count=F("support_count") + 1)
except IntegrityError:
    return SupportResult(problem, problem.support_count, already_supported=True)
```

The domain rule ("one support per person") is enforced by the database, the
cached counter moves atomically in the same transaction, and a thousand
simultaneous supporters produce exactly a thousand rows.

## Modules

Each module owns its tables and exposes behaviour through application services.
A module never reaches into a peer's ORM.

| Module | Responsibility |
| --- | --- |
| `shared` | Value objects, state machine, events, ports, API envelope, pagination, permissions |
| `accounts` | The one global identity, roles, professional profile |
| `authentication` | Google OAuth adapter, JWT issue and refresh rotation |
| `professional_verification` | Document review, Aadhaar fallback, badges, retention |
| `catalog` | Category and department hierarchies, routing rules |
| `media` | Upload validation, storage port, attachment join table |
| `problems` | Problems, support, timeline, government responses, ranking |
| `experience` | Experience & Ideas, credibility scoring, problem links |
| `comments` | Threaded discussion with depth cap and moderation states |
| `social` | Bookmarks and follows |
| `issue_clustering` | Duplicate detection and aggregation |
| `projects` | Projects, milestones, updates, proof of work |
| `funding` | Campaign and expense schema; payments off by default |
| `notifications` | Event subscribers and the notification inbox |
| `moderation` | Content reports and the moderator queue |
| `search` | Search abstraction over PostgreSQL |
| `analytics` | Public statistics and department performance |
| `audit` | Append-only record of consequential actions |
| `government` | Department membership, scoped dashboard, assignment |

## Events

Modules stay decoupled by publishing facts rather than calling each other.

```
CreateProblemUseCase
    └── records ProblemCreated
            │  (published only after the transaction commits)
            ├── issue_clustering  → enqueue duplicate detection
            ├── notifications     → alert followers
            └── search            → index
```

Events are flushed in `transaction.on_commit`, so a rolled-back write can never
have fired a notification. Handler failures are logged and swallowed: a broken
notification must not undo a citizen's report.

Deleting the whole of `notifications/application/handlers.py` would leave the
platform working, just quieter. That is the test of whether the decoupling is
real.

## What is deliberately absent

- **Microservices.** One deployable, clear module boundaries. Extraction is
  possible later along the seams already drawn; see `decisions/modular-monolith.md`.
- **Kafka.** The event bus is an interface with an in-process implementation.
  A Kafka adapter is a new file, not a rewrite.
- **Elasticsearch.** PostgreSQL full-text search behind a `SearchService`
  abstraction. See `decisions/search.md`.
- **GeoDjango.** The platform needs proximity over points, not arbitrary
  geometry. A bounding box plus haversine avoids a GDAL dependency entirely.
- **Working payments.** The schema and the gateway port exist; the default
  adapter refuses every charge. See `decisions/funding.md`.

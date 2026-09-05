# Scalability

The rule throughout: introduce a technology when a measured bottleneck demands
it, not because the diagram looks better with it.

## Stage 1 — up to ~100K users

The `docker-compose.yml` stack, deployed.

```
CDN → Next.js → load balancer → 2-4 Django instances → PostgreSQL (primary)
                                                     → Redis
                                                     → 2 Celery workers
                                                     → Cloudinary
```

What already carries this without change:

- Every list endpoint paginates, capped at 100 per page.
- Every list view batches its related data: media, viewer support state and
  link counts for a whole page are one query each, not one per card.
- Public statistics are cached for five minutes rather than aggregated per
  request. The landing page is the most-hit endpoint on the site.
- `trend_score` is stored and refreshed on engagement, not recomputed per row
  per page load.
- Duplicate detection runs in Celery, prefiltered by bounding box, category and
  time window, and capped at 200 candidates.

## Stage 2 — 100K to 1M

Add as measurement justifies, roughly in this order:

| Symptom | Response |
| --- | --- |
| Web CPU saturated | More Django instances — they are stateless |
| Read queries dominate | PostgreSQL read replica; route list and detail reads to it |
| Cache misses on hot pages | Longer TTLs; warm the landing page from a beat task |
| Queue depth growing | More Celery workers; separate queues for media and notifications |
| Media processing slow | Dedicated worker pool with its own queue |
| Slow queries appearing | `EXPLAIN ANALYZE` first, then an index — in that order |

Nothing about the code changes here. Read replicas are a `DATABASES` router;
worker pools are deployment configuration.

## Stage 3 — 1M to 10M+

| Pressure | Response | Seam that already exists |
| --- | --- | --- |
| Timeline and audit tables dominate storage | Range-partition by month | Both are append-only and always queried with a date bound |
| Full-text search too slow | OpenSearch behind `SearchService` | `SearchBackend` interface with two implementations already |
| Notification fan-out too slow | Dedicated service | Already event-driven; handlers only subscribe |
| Cross-service events needed | Kafka | `EventBus` protocol; publishers never see the implementation |
| One module needs independent scaling | Extract it | Module boundaries, no cross-module ORM access |

### Extraction order, when it is justified

`authentication` → `notifications` → `search` → `media processing` → `analytics`.

These are the modules with the fewest inbound dependencies and the clearest
contracts. `problems` and `experience` stay in the monolith longest because they
share the most.

**Extract only when a real requirement demands it:** traffic that needs
independent scaling, deployment cadence that needs independence, ownership by a
separate team, or failure isolation that actually matters. Not before.

## Performance rules the codebase holds to

Never:

- N+1 queries — list views batch their related data
- unbounded result sets — pagination is not optional
- expensive aggregates per request — cache and recompute on a schedule
- read-modify-write on counters — atomic `F()` expressions only
- media bytes in PostgreSQL
- trusting a client-supplied counter
- synchronous work the user should not have to wait for

Always:

- `select_related` / `prefetch_related` on list paths
- indexes designed from real queries, partial where the query is
- Celery for anything expensive, with idempotent and retry-safe tasks
- structured logs with request ids and latency

## Capacity notes

The bounding-box prefilter is what keeps proximity queries cheap. A `nearby`
query touches only rows inside a small latitude/longitude window via the
`(latitude, longitude)` index, then refines with the exact distance. Without it,
every proximity query would be a sequential scan with trigonometry per row.

The partial index `WHERE status IN (open statuses)` matters more each year: the
government dashboard only ever reads open issues, and resolved ones eventually
outnumber them by orders of magnitude.

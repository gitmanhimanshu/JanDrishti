# Redis as a cache, never as truth

**Status:** accepted

## Decision

Redis holds four things: cached read models, rate-limit counters, the Celery
broker, and one distributed lock. Everything in it can be recomputed from
PostgreSQL. Flushing Redis costs latency, never accuracy.

## What is cached

| Key | TTL | Recomputed from |
| --- | --- | --- |
| `public_stats:v1` | 5 min | Aggregates over problems, experiences, projects |
| Rate-limit counters | window | Nothing — losing them means a briefly generous limit |

The statistics cache matters most: the landing page is the most-hit endpoint,
and its numbers are aggregates across several tables. Recomputing them per
request would put a multi-table scan on every visit.

## What is not cached

Support counts. They are a denormalised *column*, moved atomically inside the
same transaction as the row that authorises them, and recoverable by counting
`problem_supports`. Putting them in Redis would mean a number that can disagree
with the database — on a platform whose entire value is that its numbers are
trustworthy.

## The one lock

Issue clustering. Two workers scoring near-identical reports at the same instant
could otherwise create two clusters for one pothole.

```python
with distributed_lock(f"cluster:{category}:{lat}:{lng}", timeout=30) as acquired:
    if not acquired:
        return None      # another worker has it; this task will retry
```

Everywhere else uses database constraints instead. A unique index is cheaper and
more reliable than a lock, and it cannot be forgotten. Section 49 of the spec is
explicit: Redis locks only where a genuine distributed locking requirement
exists, not everywhere.

## Degradation

With `REDIS_URL` unset the platform falls back to Django local-memory caching:

- statistics are cached per process rather than shared
- rate limits become per process
- Celery runs tasks eagerly and inline

All of which is correct for development and wrong for production, which is why
production settings refuse to boot without Redis.

## Invalidation

TTL-based, not event-based. Public statistics are five minutes stale at worst,
which is fine for a counter of problems reported.

Event-based invalidation was considered and rejected: it means every write path
knowing which cache keys it affects, which is the coupling this architecture
spends effort avoiding. TTLs are less precise and much harder to get wrong.

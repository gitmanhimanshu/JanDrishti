# PostgreSQL, and no PostGIS

**Status:** accepted

## PostgreSQL

The platform makes public claims about numbers — how many people are affected,
how many issues a department resolved, how long it took. Every one must be
reconstructible from rows, and none may drift.

That needs:

- **Real constraints.** `UNIQUE(problem_id, user_id)` is what makes duplicate
  support impossible. Not application logic that races, not a cached flag.
- **Transactions.** Insert the support row and move the cached counter together,
  or neither.
- **Partial indexes.** The government dashboard only ever reads open issues.
  As the archive grows, resolved problems dominate the table and an index that
  includes them wastes most of its size.
- **Full-text search.** Weighted, ranked, with stemming — enough that
  Elasticsearch is not needed for a long time.
- **JSONB.** Audit metadata and event payloads vary by kind; a rigid schema
  would be wrong and a separate document store would be excessive.

## Why not a document store

The data is deeply relational: a problem has a reporter, a category, a
department, a cluster, supports, comments, evidence, responses, projects.
Modelling that in documents means either duplication that drifts or joins
performed in application code.

## No PostGIS

The platform needs proximity over points, never arbitrary geometry:

- find problems within N km of a location
- find similar reports near a new one

`GeoPoint` handles both with a bounding box for the index-served prefilter and
haversine for the exact distance.

```python
min_lat, max_lat, min_lng, max_lng = point.bounding_box(radius_km)
# indexed range scan on (latitude, longitude), then refine
```

PostGIS would mean GDAL in every image and on every developer machine, a heavier
database extension, and a migration path that is awkward to reverse — in
exchange for capabilities this product does not use.

**When to revisit:** ward boundaries, catchment polygons, or "which
constituency contains this point". At that moment PostGIS is the right answer,
and `GeoPoint` is the single seam to change.

## SQLite in development

`DATABASE_URL` unset falls back to SQLite so a fresh clone runs with no
services. No PostgreSQL-only column type is used anywhere, so both work.

This is a convenience, not a supported target. CI runs the suite against
PostgreSQL, and production refuses to start on anything else.

## Identity

UUID primary keys on `User`, and a UUID `public_id` on content tables.

Sequential ids in public URLs leak how many problems have ever been reported and
make enumeration trivial. Content tables keep an integer primary key for join
performance and expose only the UUID.

Email is deliberately not the identity. It carries a unique index only because
Django requires it of `USERNAME_FIELD`; it is nullable, and nothing joins on it,
so a user changing their Google email cannot strand their reports.

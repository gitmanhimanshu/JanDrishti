# Database design

PostgreSQL. Every public-facing number can be recomputed from rows; nothing
depends on a cache being correct.

## Entity relationships

```
User (UUID pk)
 ├─1:1─ GoogleIdentity          google_subject UNIQUE — the sign-in key
 ├─1:1─ ProfessionalProfile     self-asserted, privacy-switched
 ├─1:n─ ProfessionalVerification ──1:n── VerificationDocument ──1:n── DocumentAccessLog
 ├─1:n─ Problem (reporter)
 ├─1:n─ Experience (author)
 ├─1:n─ ProblemSupport / ExperienceSupport
 ├─1:n─ Comment, Bookmark, Follow, Contribution
 └─1:n─ DepartmentMembership ──n:1── Department

Category (tree, materialised path) ──1:n── RoutingRule ──n:1── Department (tree)

Problem
 ├─n:1─ Category, Department, IssueCluster
 ├─1:n─ ProblemSupport          UNIQUE(problem, user)
 ├─1:n─ ProblemTimelineEvent    append-only
 ├─1:n─ GovernmentResponse
 ├─n:m─ Experience              via ProblemExperienceLink
 ├─n:m─ Media                   via MediaAttachment
 └─1:n─ Project

IssueCluster ──1:n── ClusterMembership ──n:1── Problem
              (originals are never deleted)

Project ──1:n── ProjectMilestone, ProjectUpdate
        └─1:n── FundingCampaign ──1:n── Contribution
                                └─1:n── Expense ── Media (receipts)
```

## Identity

`User.id` is a UUID and is what every foreign key points at. Two consequences:

- Public URLs never leak a sequential count of how many problems exist.
- A user changing the email on their Google account cannot strand their reports,
  because nothing joins on email.

Email carries a unique index only because Django requires it of `USERNAME_FIELD`
(for admin login). It is nullable, so accounts without an email are
representable, and NULL repeats freely under a unique index.

Content tables keep an integer primary key for join performance and expose an
opaque `public_id` UUID. Internal ids never appear in a response.

## Counters and concurrency

`Problem.support_count` is a denormalised cache. The authority is
`UNIQUE(problem_id, user_id)` on `problem_supports`.

```sql
-- The truth
CONSTRAINT uq_problem_support UNIQUE (problem_id, user_id)
```

Writes follow one pattern, everywhere:

1. Insert the row inside a transaction.
2. Move the counter with `F("support_count") + 1` in the same transaction.
3. Catch `IntegrityError` and report "already supported" rather than failing.

Decrements use `Greatest(F(...) - 1, 0)` because the column is unsigned and a
stale cache must never attempt to go below zero.

Read-modify-write on a Python integer is never used. Under a thousand concurrent
supporters it would lose most of them.

## Indexes

Indexes exist for queries that are actually run, not speculatively.

| Index | Serves |
| --- | --- |
| `(visibility, status, -created_at)` | The default problems list |
| `(visibility, -trend_score)` | The Trending tab |
| `(visibility, -support_count)` | Most Supported |
| `(state, district, status)` | Location filters |
| `(latitude, longitude)` | Bounding-box prefilter for Nearby and clustering |
| `(cluster, -support_count)` | Cluster detail |
| **partial** `(department, priority, -created_at) WHERE status IN (open)` | The government dashboard, which only ever reads open issues |
| **partial** `(recipient, -created_at) WHERE read_at IS NULL` | The unread notification badge |

The two partial indexes matter most over time: as the archive grows, resolved
problems and read notifications come to dominate the tables, and neither query
ever wants them.

## Check constraints

Validation lives in the domain, but the database refuses nonsense regardless:

- latitude in [-90, 90], longitude in [-180, 180]
- comment `depth <= 10`
- project `progress_percent <= 100`
- funding amounts positive, campaign totals non-negative
- one open verification request per user (partial unique)
- one open moderation report per reporter per item (partial unique)
- one current assignment per problem (partial unique)

## Geography without PostGIS

The platform needs proximity over points, not arbitrary geometry. `GeoPoint`
provides a bounding box for an index-served prefilter and a haversine distance
for the exact check.

```python
min_lat, max_lat, min_lng, max_lng = point.bounding_box(radius_km)  # index scan
# then refine with the true great-circle distance
```

The longitude delta is clamped so the box stays finite near the poles rather
than expanding to the whole planet.

This avoids a GDAL dependency in every image and every developer machine. If
polygon queries (ward boundaries, catchment areas) ever become a requirement,
PostGIS is the right answer and `GeoPoint` is the seam to change.

## Scale

- Cursor pagination for deep feeds; `OFFSET` on millions of rows is what
  eventually kills the database.
- `select_related` / `prefetch_related` on every list view. Media, support
  state and link counts for a whole page are fetched in one query each, not one
  per card.
- Soft delete on citizen content: removing a report hides it publicly while
  keeping it available to moderation and audit. Section 19 forbids destroying
  original reports.
- Partitioning is not used. It is the Stage 3 answer for the timeline and audit
  tables and should wait for a measured problem.

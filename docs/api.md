# API

Base path `/api/v1/`. Interactive schema at `/api/docs/`, OpenAPI at `/api/schema/`.

## Envelope

Every response has the same shape, so the client has one success check and one
error path.

```json
{ "success": true, "data": { }, "meta": { } }
```

```json
{
  "success": false,
  "error": { "code": "PROBLEM_NOT_FOUND", "message": "Problem not found." }
}
```

Stack traces never reach a client. Unrecognised exceptions become
`INTERNAL_ERROR` with the detail logged server-side against the request id.

### Error codes

| Code | HTTP | Meaning |
| --- | --- | --- |
| `VALIDATION_ERROR` | 400 | Input violates a rule; `details` names the fields |
| `AUTHENTICATION_REQUIRED` | 401 | Sign-in needed — the frontend opens the login prompt |
| `PERMISSION_DENIED` | 403 | Signed in, but not allowed |
| `NOT_FOUND` | 404 | No such resource |
| `CONFLICT` | 409 | Conflicts with current state |
| `ILLEGAL_STATE_TRANSITION` | 409 | Status move not allowed; `details.allowed` lists what is |
| `RATE_LIMITED` | 429 | Too many requests |
| `FEATURE_DISABLED` | 503 | Deliberately off (community funding) |
| `EXTERNAL_SERVICE_ERROR` | 502 | A dependency failed |

## Access model

Reads are public. Writes need an account. No exceptions in either direction.

| Method | Auth | Notes |
| --- | --- | --- |
| `GET`, `HEAD`, `OPTIONS` on public content | none | The default |
| Any write | required | Enforced per view, and re-checked in the use case |
| Government, moderation, audit | role + scope | Role read from the database, never the token |

## Endpoints

### Authentication

| Method | Path | Auth | Purpose |
| --- | --- | --- | --- |
| POST | `/auth/google/start/` | — | Returns a Google URL and single-use state carrying `next` |
| POST | `/auth/google/callback/` | — | Exchanges `code` or `id_token` for a session |
| POST | `/auth/refresh/` | — | Rotates the refresh token; replay revokes the family |
| POST | `/auth/signout/` | user | Revokes one session or all |

### Accounts

| Method | Path | Auth | Purpose |
| --- | --- | --- | --- |
| GET / PATCH | `/users/me/` | user | The self view (includes email) |
| POST | `/users/me/user-type/` | user | Onboarding; only CITIZEN or PROFESSIONAL are selectable |
| PUT | `/users/me/professional-profile/` | user | Self-asserted profile with privacy switches |
| GET | `/users/{id}/` | — | Public profile (never includes email) |

### Problems

| Method | Path | Auth | Purpose |
| --- | --- | --- | --- |
| GET | `/problems/` | — | List. `?tab=` selects the ranking strategy |
| GET | `/problems/tabs/` | — | The tabs, described by the strategies themselves |
| GET | `/problems/{id}/` | — | Detail with timeline, responses, evidence |
| POST | `/problems/create/` | user | Report a problem (10/hour) |
| POST / DELETE | `/problems/{id}/support/` | user | "I face this problem" (60/min) |
| POST | `/problems/{id}/evidence/` | user | Attach evidence — never marks it verified |
| POST | `/problems/{id}/responses/` | official | Government response, department-scoped |

**Tabs:** `trending`, `most_supported`, `most_reported`, `high_priority`,
`nearby`, `recent`, `recently_updated`, `resolved`, `stale`.

**Filters:** `q`, `category` (includes the subtree), `department`, `state`,
`district`, `city`, `pincode`, `status`, `priority`, `is_open`, `has_evidence`,
`verified_evidence`, `cluster`, `min_support`, `since`, `until`.

`nearby` accepts `lat`, `lng`, `radius_km`. Without coordinates it falls back to
recency rather than returning nothing.

**Create request:**

```json
{
  "title": "Streetlight outside the primary school has been dark for weeks",
  "description": "At least 30 characters describing what is wrong.",
  "category_id": "uuid", "priority": "HIGH",
  "city": "Pune", "district": "Pune", "state": "Maharashtra",
  "latitude": 18.5484, "longitude": 73.9027,
  "media_ids": ["uuid"], "is_anonymous_report": false
}
```

Either a state or GPS coordinates is required — a report that cannot be located
cannot be routed.

### Experience & Ideas

| Method | Path | Auth | Purpose |
| --- | --- | --- | --- |
| GET | `/experiences/` | — | List; `?sort=credible\|recent\|supported\|discussed` |
| GET | `/experiences/{id}/` | — | Detail |
| POST | `/experiences/create/` | user | Publish (10/hour) |
| POST / DELETE | `/experiences/{id}/support/` | user | "I support this idea" |
| POST | `/experiences/{id}/link-problem/` | user | Connect to a problem |
| GET | `/experiences/for-problem/{id}/` | — | Rendered on the problem page |

Contribution is open to any signed-in account. Verification affects how a
contribution is presented and scored, never whether it may exist.

### Comments, social, moderation

| Method | Path | Auth | Purpose |
| --- | --- | --- | --- |
| GET | `/comments/{target_type}/{id}/` | — | Whole visible thread, nested, capped at 500 |
| POST | `/comments/` | user | Comment or reply (30/min, depth-capped) |
| POST | `/comments/{id}/delete/` | owner/staff | Soft delete |
| POST | `/comments/{id}/moderate/` | moderator | Change moderation state |
| POST / DELETE | `/social/bookmarks/toggle/`, `/social/follows/toggle/` | user | Idempotent toggles |
| POST | `/moderation/report/` | user | Report content (20/hour) |
| GET | `/moderation/queue/` | moderator | Severity-ordered queue |

### Verification

| Method | Path | Auth | Purpose |
| --- | --- | --- | --- |
| POST | `/verification/documents/upload/` | user | Private upload; returns an id and **no URL** |
| POST | `/verification/submit/` | user | Submit a claim (5/day) |
| GET | `/verification/me/` | user | Own request status |
| GET | `/verification/queue/` | moderator | Review queue |
| POST | `/verification/{id}/review/` | moderator | The decision — the only writer of the badge |
| GET | `/verification/documents/{id}/access/` | moderator | Signed 5-minute URL; audited before issue |

No endpoint accepts or returns an Aadhaar number. The submit serializer has no
such field, so a client that sends one has it silently discarded.

### Government

| Method | Path | Auth | Purpose |
| --- | --- | --- | --- |
| GET | `/government/dashboard/` | official | Workload, urgency, stale counts |
| GET | `/government/problems/` | official | Department-scoped queue |
| POST | `/government/problems/{id}/status/` | official | Status change; transition + scope checked |
| POST | `/government/problems/{id}/assign/` | official | Assign to a department member |

Every queryset is scoped to the departments the official belongs to, including
the subtree beneath them. Role alone grants nothing.

### Discovery and public data

| Method | Path | Auth |
| --- | --- | --- |
| GET | `/categories/`, `/departments/`, `/states/` | — |
| GET | `/search/?q=` | — |
| GET | `/stats/public/`, `/stats/departments/` | — |
| GET | `/clusters/`, `/clusters/{id}/` | — |
| GET | `/projects/`, `/projects/{id}/` | — |
| GET | `/funding/campaigns/`, `/funding/campaigns/{id}/` | — |
| GET | `/notifications/`, `/notifications/unread-count/` | user |
| GET | `/audit/` | admin |

## Pagination

Every collection endpoint paginates. There is no way to ask this API for an
unbounded list.

```json
"meta": {
  "count": 1284, "page": 2, "page_size": 20, "total_pages": 65,
  "next": "...", "previous": "..."
}
```

`page_size` is capped at 100. Deep feeds use cursor pagination.

## Rate limits

| Scope | Limit |
| --- | --- |
| anonymous / authenticated | 120/min · 300/min |
| auth endpoints | 20/min per IP |
| support | 60/min |
| comment | 30/min |
| create problem / experience | 10/hour |
| upload | 60/hour |
| verification | 5/day |
| report content | 20/hour |

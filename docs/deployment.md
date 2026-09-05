# Deployment

## Pre-flight

Production settings refuse to boot without a strong `SECRET_KEY`, a PostgreSQL
`DATABASE_URL` and a `REDIS_URL`. A misconfigured deploy fails at start rather
than quietly serving an insecure site.

```bash
python manage.py check --deploy --fail-level WARNING
```

## Environment

| Variable | Required | Notes |
| --- | --- | --- |
| `DJANGO_SETTINGS_MODULE` | yes | `config.settings.production` |
| `SECRET_KEY` | yes | 50+ random characters; rotating it invalidates all sessions |
| `DATABASE_URL` | yes | PostgreSQL; production refuses anything else |
| `REDIS_URL` | yes | Cache, rate limiting, Celery broker |
| `ALLOWED_HOSTS` | yes | Comma-separated |
| `CORS_ALLOWED_ORIGINS` | yes | The frontend origin |
| `GOOGLE_CLIENT_ID` / `GOOGLE_CLIENT_SECRET` | for sign-in | Public browsing works without them |
| `CLOUDINARY_*` | recommended | Falls back to local disk, which does not scale across instances |
| `VERIFICATION_DOCUMENT_RETENTION_DAYS` | no | Default 180 |
| `FUNDING_PAYMENTS_ENABLED` | no | Leave false until the legal structure exists |

Secrets come from the secret manager of the hosting platform. Never from the
image, never from the repository.

## Release

```bash
python manage.py migrate --noinput
python manage.py collectstatic --noinput
gunicorn config.wsgi:application --bind 0.0.0.0:8000 --workers 4 --threads 2
```

Run migrations before rolling new application instances, and keep them
backwards-compatible for one release so old and new code can run together
during the roll:

1. Release N: add the column, nullable, write to both.
2. Release N+1: read from the new column.
3. Release N+2: drop the old one.

## Processes

| Process | Command | Scale on |
| --- | --- | --- |
| Web | `gunicorn config.wsgi:application` | Request latency, CPU |
| Worker | `celery -A config worker` | Queue depth |
| Beat | `celery -A config beat` | Exactly one, always |
| Frontend | `npm start` | Request latency |

Beat must be a singleton; two schedulers means every periodic job runs twice.

## Scheduled work

| Task | Cadence | Purpose |
| --- | --- | --- |
| `recount_clusters_task` | nightly | Reconcile cluster aggregates against member rows |
| Verification document purge | daily | Retention policy — see `security.md` |
| Public statistics warm | 5 minutes | Keep the landing page cache hot |

## Health and observability

`GET /health/` checks the database and cache and returns 503 if either is down.
Use it as the readiness probe for the load balancer; the backend image has a
`HEALTHCHECK` pointing at it.

Logs are one JSON object per line, carrying `request_id`, method, path, status
and `duration_ms`. A secret-redaction filter runs before any handler, so tokens
and Aadhaar-shaped strings never reach a log sink.

Worth alerting on: 5xx rate, p95 latency, queue depth, worker failures, Redis
memory, database connection count, OAuth failure rate, upload failure rate.

## Backups

PostgreSQL is the only source of truth; Redis holds nothing that cannot be
recomputed. Take daily full backups with point-in-time recovery, and rehearse a
restore — a backup nobody has restored is a hypothesis, not a backup.

## Scale-out

Web and worker processes are stateless: scale horizontally behind the load
balancer. Sessions live in tokens, uploads live in Cloudinary, and the cache is
shared through Redis, so no instance holds anything the others need.

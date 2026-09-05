# Development

## Requirements

Python 3.12+, Node 20+, and optionally Docker. PostgreSQL and Redis are
recommended but not required to get started.

## Fastest path

```bash
docker compose up --build
```

Backend on `:8000`, frontend on `:3000`, with PostgreSQL, Redis, a Celery worker
and beat. The backend migrates and seeds the category and department trees on
start.

## Without Docker

### Backend

```bash
cd backend
python -m venv .venv
.venv/Scripts/activate          # Windows;  source .venv/bin/activate elsewhere
pip install -r requirements-dev.txt

cp .env.example .env            # works as-is: SQLite + in-memory cache

python manage.py migrate
python manage.py seed_catalog   # categories, departments, routing rules
python manage.py createsuperuser
python manage.py runserver
```

With `DATABASE_URL` and `REDIS_URL` unset the backend falls back to SQLite and a
local-memory cache, so a fresh clone runs with no services at all. No
PostgreSQL-only column type is used anywhere, so both backends work — but run
the suite against PostgreSQL before trusting a change to search or indexes.

### Frontend

```bash
cd frontend
npm install
cp .env.local.example .env.local
npm run dev
```

### Celery

```bash
cd backend
celery -A config worker --loglevel=info
celery -A config beat --loglevel=info
```

Without `REDIS_URL`, `CELERY_TASK_ALWAYS_EAGER` is on and tasks run inline —
convenient in development, and the reason the test suite exercises the
clustering path without a broker.

## Google OAuth

1. Create an OAuth client at <https://console.cloud.google.com/apis/credentials>.
2. Authorised JavaScript origin: `http://localhost:3000`.
3. Authorised redirect URI: `http://localhost:3000/auth/callback`.
4. Put the client id and secret in `backend/.env`, and the client id in
   `frontend/.env.local` as `NEXT_PUBLIC_GOOGLE_CLIENT_ID`.

Without these, sign-in returns a clear "not configured" error and everything
public still works — which is most of the platform.

## Tests

```bash
cd backend
pytest                          # 160 tests
pytest tests/test_domain.py     # pure domain, no database, about a second
pytest --cov=jandrishti --cov-report=term-missing
```

| File | Covers |
| --- | --- |
| `test_domain.py` | Value objects, lifecycle, ranking, clustering scores, credibility |
| `test_api_public_access.py` | The public-first contract: anonymous reads, gated writes |
| `test_problems.py` | Creation, routing, support concurrency, transitions, tabs, filters |
| `test_experience_and_social.py` | Publishing, credibility, comments, nesting caps, bookmarks |
| `test_clustering.py` | Merging, and that original reports are never destroyed |
| `test_security.py` | Escalation, IDOR, tokens, uploads, Aadhaar, redaction |

## Quality gates

```bash
cd backend
ruff check .          # lint
ruff format .         # format
mypy jandrishti       # types
python manage.py makemigrations --check --dry-run

cd ../frontend
npm run typecheck
npm run lint
npm run build
```

CI runs all of these plus `bandit`, `pip-audit`, a committed-secret scan, and
`manage.py check --deploy` under production settings.

## Where to put things

| Kind of change | Where |
| --- | --- |
| A business rule | `modules/<module>/domain/` — no framework imports |
| An action a user takes | `modules/<module>/application/` — a use case |
| An external service | `modules/<module>/infrastructure/` — behind a port |
| An endpoint | `modules/<module>/api/` — thin: validate, call, serialise |
| A new problems tab | One `RankingStrategy` subclass, registered. Nothing else changes |
| Reacting to something | Subscribe to a domain event; do not call the other module |

If a view is getting long, the logic belongs in a use case. If a use case is
branching on business rules, they belong in the domain.

## Adding a ranking tab, end to end

```python
class MostDiscussedRankingStrategy(RankingStrategy):
    key = "most_discussed"
    label = "Most Discussed"
    description = "Where the conversation is."

    def apply(self, queryset, **context):
        return queryset.order_by("-comment_count", "-created_at")

ranking_registry.register(MostDiscussedRankingStrategy())
```

That is the whole change. The tab appears in `/problems/tabs/`, the frontend
renders it from that response, and no existing strategy was touched.

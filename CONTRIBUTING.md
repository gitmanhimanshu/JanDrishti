# Contributing

## Before you open a pull request

```bash
cd backend
ruff check . && ruff format --check .
python manage.py makemigrations --check --dry-run
pytest

cd ../frontend
npm run typecheck && npm run lint && npm run build
```

CI runs all of this, plus a security scan and a committed-secret check.

## Where code belongs

| Change | Layer |
| --- | --- |
| A business rule | `modules/<module>/domain/` - pure Python, no framework imports |
| An action a user performs | `modules/<module>/application/` - a use case |
| Talking to an external service | `modules/<module>/infrastructure/` - behind a port |
| An HTTP endpoint | `modules/<module>/api/` - thin |

A view that grew logic wants a use case. A use case branching on business rules
wants the domain.

## Rules that are not negotiable

These have tests, and a pull request that breaks one will fail CI:

1. **Public reads stay public.** No login requirement on reading public content.
2. **Every write is authorized server-side**, against the role in the database.
3. **No client-supplied counter is trusted.** Constraints decide; cached columns
   follow atomically.
4. **Nothing automated marks evidence verified**, or grants a professional badge.
5. **Original citizen reports are never deleted.** Soft delete only.
6. **No Aadhaar number is stored, logged, returned or put in a URL.**
7. **Every collection endpoint paginates.**

## Adding a module

Create `domain/`, `application/`, `infrastructure/`, `api/`, `migrations/`, add
an `AppConfig` with an explicit `label`, register it in `LOCAL_APPS`, and add
one line to `config/urls.py`.

Do not import another module's models. Read through its application service;
react through domain events.

## Commit messages

Explain why, not what. The diff shows what changed.

# PostgreSQL full-text search, not Elasticsearch

**Status:** accepted

## Decision

Search through a `SearchService` facade with two backends: PostgreSQL full-text
search in production, a portable `ILIKE` fallback on SQLite.

## Why not Elasticsearch now

Elasticsearch is a genuinely better search engine. It is also a second
datastore to run, secure, back up, monitor and keep in sync — and an
indexing pipeline whose lag is visible to users as "I posted it, why can I not
find it".

PostgreSQL provides weighted fields, ranking, stemming and phrase queries. On a
corpus of civic reports that is enough for a long time.

```python
vector = (SearchVector("title", weight="A")
          + SearchVector("description", weight="B")
          + SearchVector("city", "district", "state", weight="C"))
```

Title outranks body, so a report *about* potholes beats one that merely mentions
them.

## The seam

```
Callers  →  SearchService  →  SearchBackend
                              ├── PostgresSearchBackend   (production)
                              └── SimpleSearchBackend     (SQLite fallback)
```

Every caller — the problems filter, the experience filter, unified search —
goes through the facade. Adding `OpenSearchBackend` means one new class and one
line in the factory.

The backend is chosen from `connection.vendor` at first use, so the same code
runs on both databases without configuration.

## When to revisit

Concrete triggers, not a user count:

- search p95 above ~500ms on a warm cache
- a real need for fuzzy matching, synonyms or aggregation facets
- multilingual search across Indian languages, where PostgreSQL dictionary
  support becomes the limiting factor

The last one is the likeliest. When it arrives, the indexing pipeline hangs off
the existing domain events (`ProblemCreated`, `ExperienceCreated`), which are
already published.

## Not done deliberately

No search index table, no denormalised search columns, no trigram extension
until a query demands one. Each is a real technique; none has earned its
maintenance cost yet.

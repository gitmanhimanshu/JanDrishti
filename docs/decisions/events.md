# In-process events, not Kafka

**Status:** accepted

## Context

Creating a problem should trigger duplicate detection, notify followers, index
for search and update analytics. Wiring those directly into
`CreateProblemUseCase` would make the problems module depend on four others.

## Decision

Publish domain events to an in-process bus. Handlers subscribe by name at
app-ready time. Anything that must not be lost hands off to Celery.

## Why not Kafka now

Kafka solves cross-service durability, replay and ordering across a
distributed system. This is one process with one database, so:

- delivery to a handler is a function call that cannot fail in transit
- durability comes from Celery, backed by Redis, for the handlers that need it
- ordering is guaranteed by running inside one transaction

Adding Kafka now buys a broker to operate, a serialisation format to version,
consumer group semantics to reason about, and a new failure mode — in exchange
for guarantees that a single process already has.

## The seam that makes it reversible

Publishers depend on the `EventBus` protocol and a frozen `DomainEvent`
dataclass. Nothing in the domain or application layers knows the bus is
in-process.

```python
class EventBus(Protocol):
    def publish(self, event: DomainEvent) -> None: ...
    def publish_many(self, events: Iterable[DomainEvent]) -> None: ...
```

Introducing Kafka means writing one adapter that satisfies this protocol.
No publisher changes. `DomainEvent.to_dict()` already produces a serialisable
payload with an event id and timestamp.

## Two properties that matter

**Events publish after commit.** Use cases collect events and flush them in
`transaction.on_commit`, so a rolled-back write can never have fired a
notification.

```python
with transaction.atomic():
    result = self.handle(request)
    transaction.on_commit(lambda: self._event_bus.publish_many(events))
```

**Handler failures are isolated.** A handler that raises is logged and
swallowed. A broken notification must never undo the citizen's report that
triggered it.

## Consequences

Good: modules stay decoupled, tests run without a broker, adding a reaction to
an existing action requires touching only the new handler.

Bad: an event is lost if the process dies between commit and handler execution.
Acceptable, because handlers whose loss would matter (clustering) enqueue a
Celery task rather than doing the work inline — and those tasks are idempotent,
so a retry is safe.

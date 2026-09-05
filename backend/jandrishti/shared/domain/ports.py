"""
Ports: the interfaces the domain and application layers depend on.

Every one of these is implemented in an infrastructure adapter. Domain code
imports the Protocol, never Cloudinary, Redis, Google or an AI SDK -- that is
the whole of the dependency inversion rule in this codebase.
"""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any, Protocol, runtime_checkable

from .events import DomainEvent


@runtime_checkable
class EventBus(Protocol):
    """Publishes domain events to whatever is listening."""

    def publish(self, event: DomainEvent) -> None: ...

    def publish_many(self, events: Iterable[DomainEvent]) -> None: ...


@runtime_checkable
class Clock(Protocol):
    """Injectable time, so time-dependent rules are testable without sleeping."""

    def now(self) -> Any: ...


@runtime_checkable
class CacheGateway(Protocol):
    def get(self, key: str) -> Any: ...

    def set(self, key: str, value: Any, ttl_seconds: int | None = None) -> None: ...

    def delete(self, key: str) -> None: ...

    def get_or_set(self, key: str, producer: Any, ttl_seconds: int | None = None) -> Any: ...


@runtime_checkable
class Repository(Protocol):
    """Minimal persistence port. Modules extend this with their own methods."""

    def get(self, entity_id: Any) -> Any: ...

    def add(self, entity: Any) -> Any: ...

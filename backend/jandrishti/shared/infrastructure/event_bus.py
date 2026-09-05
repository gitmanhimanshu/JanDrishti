"""
In-process event bus.

Handlers register by event name at app-ready time. A handler that throws is
logged and swallowed: a failing notification must never roll back the problem
report that triggered it. Handlers that must not be lost hand off to Celery.

Replacing this with Kafka means writing one more adapter that satisfies the
EventBus protocol -- no publisher changes. See docs/decisions/events.md.
"""

from __future__ import annotations

import logging
from collections import defaultdict
from collections.abc import Callable, Iterable

from ..domain.events import DomainEvent

logger = logging.getLogger(__name__)

Handler = Callable[[DomainEvent], None]


class InProcessEventBus:
    def __init__(self) -> None:
        self._handlers: dict[str, list[Handler]] = defaultdict(list)

    def subscribe(self, event_name: str, handler: Handler) -> None:
        if handler not in self._handlers[event_name]:
            self._handlers[event_name].append(handler)

    def publish(self, event: DomainEvent) -> None:
        handlers = self._handlers.get(event.name, ())
        if not handlers:
            logger.debug("event %s published with no subscribers", event.name)
        for handler in handlers:
            try:
                handler(event)
            except Exception:
                logger.exception(
                    "event handler failed",
                    extra={"event": event.name, "handler": getattr(handler, "__name__", "?")},
                )

    def publish_many(self, events: Iterable[DomainEvent]) -> None:
        for event in events:
            self.publish(event)

    def clear(self) -> None:
        """Test helper."""
        self._handlers.clear()


_bus = InProcessEventBus()


def get_event_bus() -> InProcessEventBus:
    return _bus


def subscribe(event_name: str) -> Callable[[Handler], Handler]:
    """Decorator form: @subscribe(Events.PROBLEM_CREATED)."""

    def decorator(handler: Handler) -> Handler:
        _bus.subscribe(event_name, handler)
        return handler

    return decorator

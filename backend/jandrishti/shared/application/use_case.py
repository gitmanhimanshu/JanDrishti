"""
Use case base.

An application service holds one unit of intent -- CreateProblem,
SupportProblem, UpdateProblemStatus. It orchestrates: it loads through
repositories, calls domain rules, persists in one transaction, and publishes
events. It never contains a business rule itself, and it never touches HTTP.
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Generic, TypeVar

from django.db import transaction

from ..domain.events import DomainEvent
from ..domain.exceptions import AuthenticationRequiredError, PermissionDeniedError

logger = logging.getLogger(__name__)

TInput = TypeVar("TInput")
TOutput = TypeVar("TOutput")


@dataclass(slots=True)
class Actor:
    """Who is asking. Anonymous is a first-class citizen on this platform."""

    user: Any = None
    ip_address: str = ""
    user_agent: str = ""
    request_id: str = ""

    @property
    def is_authenticated(self) -> bool:
        return bool(self.user is not None and getattr(self.user, "is_authenticated", False))

    @property
    def id(self) -> Any:
        return getattr(self.user, "id", None)

    def require_authenticated(self) -> Any:
        if not self.is_authenticated:
            raise AuthenticationRequiredError()
        return self.user

    def require_role(self, *roles: str) -> Any:
        user = self.require_authenticated()
        if getattr(user, "role", None) not in roles and not getattr(user, "is_superuser", False):
            raise PermissionDeniedError("Your account does not have access to this action.")
        return user

    @classmethod
    def anonymous(cls) -> Actor:
        return cls()


class UseCase(ABC, Generic[TInput, TOutput]):
    """Base class for application services.

    `execute` runs the whole thing in a transaction and flushes collected
    events only after the commit succeeds, so a rolled-back write can never
    have fired a notification.
    """

    def __init__(self, event_bus: Any = None) -> None:
        from ..infrastructure.event_bus import get_event_bus

        self._event_bus = event_bus or get_event_bus()
        self._pending_events: list[DomainEvent] = []

    def record(self, event: DomainEvent) -> None:
        self._pending_events.append(event)

    @abstractmethod
    def handle(self, request: TInput) -> TOutput:
        """The actual work. Implemented by each use case."""

    def execute(self, request: TInput) -> TOutput:
        with transaction.atomic():
            result = self.handle(request)
            events = list(self._pending_events)
            self._pending_events.clear()
            if events:
                transaction.on_commit(lambda: self._event_bus.publish_many(events))
        return result

    def __call__(self, request: TInput) -> TOutput:
        return self.execute(request)


@dataclass(slots=True)
class Command:
    """Base for use case inputs: a plain DTO carrying the actor plus data."""

    actor: Actor = field(default_factory=Actor.anonymous)

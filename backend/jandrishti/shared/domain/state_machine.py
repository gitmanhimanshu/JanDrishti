"""
A reusable, explicit state machine.

Section 33 of the spec is emphatic: no arbitrary status strings. Statuses move
along a declared graph, and an illegal move raises rather than silently writing
a nonsense status. The problem lifecycle is the main user, but projects and
verification use the same primitive.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from typing import Generic, TypeVar

from .exceptions import IllegalStateTransitionError

S = TypeVar("S")


@dataclass(frozen=True, slots=True)
class Transition(Generic[S]):
    source: S
    target: S
    label: str = ""


class StateMachine(Generic[S]):
    """Declares which states may follow which, and who may make the move."""

    def __init__(
        self,
        transitions: Mapping[S, Iterable[S]],
        *,
        terminal: Iterable[S] = (),
        name: str = "state",
    ) -> None:
        self._transitions: dict[S, frozenset[S]] = {
            source: frozenset(targets) for source, targets in transitions.items()
        }
        self._terminal = frozenset(terminal)
        self._name = name

    def allowed_from(self, source: S) -> frozenset[S]:
        return self._transitions.get(source, frozenset())

    def can(self, source: S, target: S) -> bool:
        return target in self.allowed_from(source)

    def is_terminal(self, state: S) -> bool:
        return state in self._terminal

    def assert_can(self, source: S, target: S) -> None:
        if source == target:
            raise IllegalStateTransitionError(
                f"The {self._name} is already {source}.",
                details={"from": str(source), "to": str(target)},
            )
        if not self.can(source, target):
            allowed = sorted(str(s) for s in self.allowed_from(source))
            raise IllegalStateTransitionError(
                f"Cannot move {self._name} from {source} to {target}.",
                details={"from": str(source), "to": str(target), "allowed": allowed},
            )

    def transition(self, source: S, target: S) -> S:
        self.assert_can(source, target)
        return target

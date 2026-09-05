"""
Cache adapter and a Redis-backed lock.

Redis is a cache and a coordination tool here, never a source of truth: every
number it holds can be recomputed from PostgreSQL. Counters are read from the
database aggregate on a miss, so a flushed Redis costs latency, not accuracy.
"""

from __future__ import annotations

import contextlib
import logging
import uuid
from collections.abc import Callable, Iterator
from typing import Any

from django.core.cache import cache as django_cache

logger = logging.getLogger(__name__)

DEFAULT_TTL = 60


class DjangoCacheGateway:
    """Implements the CacheGateway port on top of the configured Django cache."""

    def __init__(self, prefix: str = "jd") -> None:
        self._prefix = prefix

    def _key(self, key: str) -> str:
        return f"{self._prefix}:{key}"

    def get(self, key: str) -> Any:
        return django_cache.get(self._key(key))

    def set(self, key: str, value: Any, ttl_seconds: int | None = DEFAULT_TTL) -> None:
        django_cache.set(self._key(key), value, ttl_seconds)

    def delete(self, key: str) -> None:
        django_cache.delete(self._key(key))

    def get_or_set(
        self, key: str, producer: Callable[[], Any], ttl_seconds: int | None = DEFAULT_TTL
    ) -> Any:
        namespaced = self._key(key)
        value = django_cache.get(namespaced)
        if value is None:
            value = producer()
            django_cache.set(namespaced, value, ttl_seconds)
        return value

    def incr(self, key: str, delta: int = 1) -> int | None:
        """Best-effort counter bump. Returns None if the key is not cached.

        Callers must treat None as `nothing to do` -- the authoritative count
        still lives in PostgreSQL.
        """
        try:
            return django_cache.incr(self._key(key), delta)
        except ValueError:
            return None


cache_gateway = DjangoCacheGateway()


@contextlib.contextmanager
def distributed_lock(name: str, timeout: int = 30) -> Iterator[bool]:
    """A mutex across processes, for the few places that genuinely need one.

    Used by issue clustering, where two workers examining near-identical reports
    at the same moment could otherwise create two clusters for one pothole.
    Ordinary write paths use database constraints instead -- a unique index is
    cheaper and more reliable than a lock. See section 49 of the spec.
    """
    key = f"jd:lock:{name}"
    token = uuid.uuid4().hex
    acquired = django_cache.add(key, token, timeout)
    try:
        yield bool(acquired)
    finally:
        if acquired and django_cache.get(key) == token:
            django_cache.delete(key)

"""
Search service (spec 52).

Start with the database you already have. PostgreSQL full-text search handles
the volumes this platform will see for a long time, and it comes with no extra
cluster to operate. Elasticsearch is a real answer to a real problem -- but the
problem has to exist first (spec 74).

What matters architecturally is the seam: everything searches through this
service, so introducing an OpenSearch backend later means writing one adapter
and changing one factory.
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod

from django.db import connection
from django.db.models import Q, QuerySet

logger = logging.getLogger(__name__)

MIN_QUERY_LENGTH = 2


class SearchBackend(ABC):
    name: str

    @abstractmethod
    def filter_problems(self, queryset: QuerySet, query: str) -> QuerySet: ...

    @abstractmethod
    def filter_experiences(self, queryset: QuerySet, query: str) -> QuerySet: ...


class SimpleSearchBackend(SearchBackend):
    """Portable ILIKE search.

    Used on SQLite and as the fallback everywhere. Honest about its limits: no
    stemming, no ranking. Adequate for a development database, not for a
    production corpus.
    """

    name = "simple"

    def filter_problems(self, queryset: QuerySet, query: str) -> QuerySet:
        return queryset.filter(
            Q(title__icontains=query)
            | Q(description__icontains=query)
            | Q(city__icontains=query)
            | Q(district__icontains=query)
        )

    def filter_experiences(self, queryset: QuerySet, query: str) -> QuerySet:
        return queryset.filter(
            Q(title__icontains=query)
            | Q(recommendation__icontains=query)
            | Q(personal_experience__icontains=query)
            | Q(root_cause__icontains=query)
        )


class PostgresSearchBackend(SearchBackend):
    """PostgreSQL full-text search with weighted fields and relevance ranking.

    The title is weighted above the body so that a report *about* potholes
    outranks one that merely mentions them.
    """

    name = "postgres"

    def filter_problems(self, queryset: QuerySet, query: str) -> QuerySet:
        from django.contrib.postgres.search import SearchQuery, SearchRank, SearchVector

        vector = (
            SearchVector("title", weight="A")
            + SearchVector("description", weight="B")
            + SearchVector("city", "district", "state", weight="C")
        )
        search_query = SearchQuery(query, search_type="websearch")
        return (
            queryset.annotate(rank=SearchRank(vector, search_query))
            .filter(rank__gt=0.01)
            .order_by("-rank")
        )

    def filter_experiences(self, queryset: QuerySet, query: str) -> QuerySet:
        from django.contrib.postgres.search import SearchQuery, SearchRank, SearchVector

        vector = (
            SearchVector("title", weight="A")
            + SearchVector("recommendation", weight="B")
            + SearchVector("personal_experience", "root_cause", weight="C")
        )
        search_query = SearchQuery(query, search_type="websearch")
        return (
            queryset.annotate(rank=SearchRank(vector, search_query))
            .filter(rank__gt=0.01)
            .order_by("-rank")
        )


class SearchService:
    """The facade every caller uses."""

    def __init__(self, backend: SearchBackend | None = None) -> None:
        self._backend = backend

    @property
    def backend(self) -> SearchBackend:
        if self._backend is None:
            self._backend = (
                PostgresSearchBackend()
                if connection.vendor == "postgresql"
                else SimpleSearchBackend()
            )
        return self._backend

    @staticmethod
    def _clean(query: str) -> str:
        return (query or "").strip()[:200]

    def filter_problems(self, queryset: QuerySet, query: str) -> QuerySet:
        query = self._clean(query)
        if len(query) < MIN_QUERY_LENGTH:
            return queryset
        return self.backend.filter_problems(queryset, query)

    def filter_experiences(self, queryset: QuerySet, query: str) -> QuerySet:
        query = self._clean(query)
        if len(query) < MIN_QUERY_LENGTH:
            return queryset
        return self.backend.filter_experiences(queryset, query)


search_service = SearchService()

"""
Pagination.

Every collection endpoint paginates -- there is no way to ask this API for an
unbounded list (spec 48). Two styles:

* StandardPageNumberPagination for browsable, filterable, sortable lists where
  the user expects page numbers and a total.
* CursorPagination for deep feeds and comment threads, where OFFSET on a table
  with millions of rows is the thing that eventually kills the database.
"""

from __future__ import annotations

from collections import OrderedDict
from typing import Any

from rest_framework.pagination import CursorPagination, PageNumberPagination
from rest_framework.response import Response

MAX_PAGE_SIZE = 100


class StandardPageNumberPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = "page_size"
    max_page_size = MAX_PAGE_SIZE

    def get_paginated_response(self, data: Any) -> Response:
        return Response(
            {
                "success": True,
                "data": data,
                "meta": OrderedDict(
                    [
                        ("count", self.page.paginator.count),
                        ("page", self.page.number),
                        ("page_size", self.get_page_size(self.request)),
                        ("total_pages", self.page.paginator.num_pages),
                        ("next", self.get_next_link()),
                        ("previous", self.get_previous_link()),
                    ]
                ),
            }
        )


class TimelineCursorPagination(CursorPagination):
    """Newest-first cursor feed. Stable under concurrent inserts."""

    page_size = 20
    page_size_query_param = "page_size"
    max_page_size = MAX_PAGE_SIZE
    ordering = "-created_at"
    cursor_query_param = "cursor"

    def get_paginated_response(self, data: Any) -> Response:
        return Response(
            {
                "success": True,
                "data": data,
                "meta": {
                    "page_size": self.get_page_size(self.request),
                    "next": self.get_next_link(),
                    "previous": self.get_previous_link(),
                },
            }
        )

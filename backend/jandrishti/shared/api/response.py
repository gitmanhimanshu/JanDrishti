"""
The single API envelope.

Every response the platform emits has the same shape, so the frontend has one
success check and one error path rather than per-endpoint guesswork (spec 54).
"""

from __future__ import annotations

from typing import Any

from rest_framework.response import Response


def ok(data: Any = None, *, status: int = 200, meta: dict[str, Any] | None = None) -> Response:
    body: dict[str, Any] = {"success": True, "data": data}
    if meta:
        body["meta"] = meta
    return Response(body, status=status)


def created(data: Any = None, **kwargs: Any) -> Response:
    return ok(data, status=201, **kwargs)


def no_content() -> Response:
    return Response({"success": True, "data": None}, status=200)


def error(
    code: str,
    message: str,
    *,
    status: int = 400,
    details: dict[str, Any] | None = None,
) -> Response:
    body: dict[str, Any] = {"success": False, "error": {"code": code, "message": message}}
    if details:
        body["error"]["details"] = details
    return Response(body, status=status)

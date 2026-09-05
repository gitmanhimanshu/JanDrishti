"""
Structured logging with a hard redaction filter.

Section 64: tokens, OAuth secrets, Aadhaar numbers and verification document
references must never reach a log sink. Redaction lives in a filter rather than
in call sites, because relying on every future call site to remember is how
secrets end up in logs.
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any

SENSITIVE_KEYS = {
    "password",
    "token",
    "access_token",
    "refresh_token",
    "id_token",
    "authorization",
    "secret",
    "client_secret",
    "api_key",
    "aadhaar",
    "aadhaar_number",
    "aadhaar_reference",
    "document_url",
    "document_storage_key",
    "otp",
    "signature",
}

# 12 digits, optionally spaced in groups of four -- an Aadhaar-shaped string.
AADHAAR_RE = re.compile(r"\b\d{4}[ -]?\d{4}[ -]?\d{4}\b")
BEARER_RE = re.compile(r"(Bearer\s+)[A-Za-z0-9._\-]+", re.IGNORECASE)
JWT_RE = re.compile(r"\beyJ[A-Za-z0-9._\-]{10,}\b")

REDACTED = "[REDACTED]"


def scrub(value: Any) -> Any:
    """Recursively redact sensitive keys and secret-shaped strings."""
    if isinstance(value, dict):
        return {
            key: (REDACTED if str(key).lower() in SENSITIVE_KEYS else scrub(item))
            for key, item in value.items()
        }
    if isinstance(value, list | tuple):
        return [scrub(item) for item in value]
    if isinstance(value, str):
        text = BEARER_RE.sub(r"\1" + REDACTED, value)
        text = JWT_RE.sub(REDACTED, text)
        return AADHAAR_RE.sub(REDACTED, text)
    return value


class SecretRedactionFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        if isinstance(record.msg, str):
            record.msg = scrub(record.msg)
        elif isinstance(record.msg, dict):
            record.msg = scrub(record.msg)
        if record.args:
            record.args = (
                scrub(dict(record.args))
                if isinstance(record.args, dict)
                else tuple(scrub(arg) for arg in record.args)
            )
        return True


_RESERVED = set(logging.LogRecord("", 0, "", 0, "", (), None).__dict__) | {
    "asctime",
    "message",
    "taskName",
}


class JsonFormatter(logging.Formatter):
    """One JSON object per line -- what log aggregators actually want."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "time": self.formatTime(record, "%Y-%m-%dT%H:%M:%S%z"),
        }
        for key, value in record.__dict__.items():
            if key not in _RESERVED and not key.startswith("_"):
                payload[key] = scrub(value)
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, default=str)

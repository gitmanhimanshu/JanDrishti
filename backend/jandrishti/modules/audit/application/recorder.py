"""
The one function other modules call to write an audit record.

It is intentionally forgiving: an audit failure logs loudly but never breaks the
user action that triggered it, because a government official being unable to
acknowledge an issue is worse than a missing log line. Metadata is scrubbed on
the way in so a careless caller cannot log a token.
"""

from __future__ import annotations

import logging
from typing import Any

from jandrishti.shared.infrastructure.logging import scrub

logger = logging.getLogger(__name__)


def record_audit(
    *,
    action: str,
    actor: Any = None,
    target: str = "",
    metadata: dict[str, Any] | None = None,
    ip_address: str | None = None,
    request_id: str = "",
) -> None:
    from ..models import AuditLog

    try:
        AuditLog.objects.create(
            action=action,
            actor=actor if getattr(actor, "pk", None) else None,
            actor_label=str(actor) if actor else "system",
            target=target,
            metadata=scrub(metadata or {}),
            ip_address=ip_address or None,
            request_id=request_id,
        )
    except Exception:
        logger.exception("failed to write audit record", extra={"action": action, "target": target})

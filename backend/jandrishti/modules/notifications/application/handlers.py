"""
Event handlers that turn domain events into notifications.

This module is the reason `problems` does not import `notifications`. Problems
publishes a fact; this subscribes to it. Deleting this whole file would leave
the rest of the platform working, just quieter -- which is the test of whether
the decoupling is real.
"""

from __future__ import annotations

import logging

from jandrishti.modules.social.models import Follow, TargetType
from jandrishti.shared.domain.events import DomainEvent, Events
from jandrishti.shared.infrastructure.event_bus import subscribe

from ..models import Notification, NotificationKind

logger = logging.getLogger(__name__)

# Fan-out cap. Beyond this the work moves to a Celery task rather than blocking
# the publishing request.
INLINE_FANOUT_LIMIT = 50


def _notify(recipient_id, kind: str, title: str, body: str, link_path: str, **metadata) -> None:
    if recipient_id is None:
        return
    Notification.objects.create(
        recipient_id=recipient_id,
        kind=kind,
        title=title[:200],
        body=body[:500],
        link_path=link_path[:300],
        metadata=metadata,
    )


def _followers(target_type: str, target_id: int, exclude_user_id=None) -> list:
    queryset = Follow.objects.filter(
        target_type=target_type, target_id=target_id, notifications_enabled=True
    )
    if exclude_user_id:
        queryset = queryset.exclude(user_id=exclude_user_id)
    return list(queryset.values_list("user_id", flat=True)[:5000])


@subscribe(Events.PROBLEM_STATUS_CHANGED)
def on_problem_status_changed(event: DomainEvent) -> None:
    """Tell the reporter and every follower that something moved."""
    from jandrishti.modules.problems.models import Problem

    problem = Problem.objects.filter(pk=event.payload.get("problem_pk")).first()
    if problem is None:
        return

    title = f"Update on: {problem.title[:80]}"
    body = f"Status changed to {problem.get_status_display()}."
    link = f"/problems/{problem.public_id}"

    recipients = set(_followers(TargetType.PROBLEM, problem.id))
    if problem.reporter_id:
        recipients.add(problem.reporter_id)
    # Everyone who said they face this problem has a stake in the answer.
    recipients.update(problem.supports.values_list("user_id", flat=True)[:INLINE_FANOUT_LIMIT])

    notifications = [
        Notification(
            recipient_id=recipient_id,
            kind=NotificationKind.PROBLEM_STATUS_CHANGED,
            title=title,
            body=body,
            link_path=link,
            metadata={"problem_id": str(problem.public_id), "status": problem.status},
        )
        for recipient_id in recipients
    ]
    Notification.objects.bulk_create(notifications, batch_size=500)


@subscribe(Events.GOVERNMENT_RESPONSE_ADDED)
def on_government_response(event: DomainEvent) -> None:
    from jandrishti.modules.problems.models import Problem

    problem = Problem.objects.filter(pk=event.payload.get("problem_pk")).first()
    if problem is None:
        return
    recipients = set(_followers(TargetType.PROBLEM, problem.id))
    if problem.reporter_id:
        recipients.add(problem.reporter_id)
    Notification.objects.bulk_create(
        [
            Notification(
                recipient_id=recipient_id,
                kind=NotificationKind.GOVERNMENT_RESPONSE,
                title=f"Official response: {problem.title[:70]}",
                body="A department has responded to this issue.",
                link_path=f"/problems/{problem.public_id}",
                metadata={"problem_id": str(problem.public_id)},
            )
            for recipient_id in recipients
        ],
        batch_size=500,
    )


@subscribe(Events.COMMENT_CREATED)
def on_comment_created(event: DomainEvent) -> None:
    """Notify the parent commenter, then the content author -- once each."""
    payload = event.payload
    author_id = payload.get("author_id")
    notified: set = set()

    parent_author_id = payload.get("parent_author_id")
    if parent_author_id and parent_author_id != author_id:
        _notify(
            parent_author_id,
            NotificationKind.COMMENT_REPLY,
            "Someone replied to your comment",
            "",
            _link_for(payload),
            comment_id=payload.get("comment_id"),
        )
        notified.add(parent_author_id)

    content_author_id = _content_author_id(payload)
    if (
        content_author_id
        and content_author_id not in notified
        and str(content_author_id) != str(author_id)
    ):
        _notify(
            content_author_id,
            NotificationKind.COMMENT_ON_CONTENT,
            "New comment on your post",
            "",
            _link_for(payload),
            comment_id=payload.get("comment_id"),
        )


def _link_for(payload: dict) -> str:
    target_type = payload.get("target_type")
    public_id = payload.get("target_public_id")
    prefix = {"PROBLEM": "problems", "EXPERIENCE": "experience", "PROJECT": "projects"}.get(
        target_type, "problems"
    )
    return f"/{prefix}/{public_id}"


def _content_author_id(payload: dict):
    target_type = payload.get("target_type")
    target_pk = payload.get("target_pk")
    if target_type == "PROBLEM":
        from jandrishti.modules.problems.models import Problem

        return Problem.objects.filter(pk=target_pk).values_list("reporter_id", flat=True).first()
    if target_type == "EXPERIENCE":
        from jandrishti.modules.experience.models import Experience

        return Experience.objects.filter(pk=target_pk).values_list("author_id", flat=True).first()
    return None


@subscribe(Events.VERIFICATION_COMPLETED)
def on_verification_completed(event: DomainEvent) -> None:
    decision = event.payload.get("decision")
    verified = decision == "VERIFIED"
    _notify(
        event.payload.get("user_id"),
        NotificationKind.VERIFICATION_RESULT,
        "Your professional verification was approved"
        if verified
        else "Your professional verification needs attention",
        "Your verified badge is now visible on your contributions."
        if verified
        else "Open your verification request to see what the reviewer needs.",
        "/profile/verification",
        decision=decision,
    )


@subscribe(Events.PROBLEM_SUPPORTED)
def on_problem_supported(event: DomainEvent) -> None:
    """Tell the reporter at meaningful milestones, not on every single support.

    A report that reaches 500 supporters would otherwise generate 500 alerts
    for one person.
    """
    count = event.payload.get("support_count", 0)
    if count not in {10, 50, 100, 500, 1000, 5000}:
        return

    from jandrishti.modules.problems.models import Problem

    problem = Problem.objects.filter(pk=event.payload.get("problem_pk")).first()
    if problem is None or not problem.reporter_id:
        return
    _notify(
        problem.reporter_id,
        NotificationKind.SUPPORT_MILESTONE,
        f"{count} people now support your report",
        problem.title[:200],
        f"/problems/{problem.public_id}",
        support_count=count,
    )


@subscribe(Events.PROJECT_UPDATED)
def on_project_updated(event: DomainEvent) -> None:
    project_pk = event.payload.get("project_pk")
    recipients = _followers(TargetType.PROJECT, project_pk)
    Notification.objects.bulk_create(
        [
            Notification(
                recipient_id=recipient_id,
                kind=NotificationKind.PROJECT_UPDATE,
                title="Project update",
                body=event.payload.get("title", "")[:500],
                link_path=f"/projects/{event.payload.get('project_id')}",
            )
            for recipient_id in recipients
        ],
        batch_size=500,
    )

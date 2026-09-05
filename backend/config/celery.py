"""Celery application.

Background work is for anything the user should not wait on: media processing,
duplicate detection, clustering, notifications, analytics rollups. Tasks are
written to be idempotent and retry-safe -- see docs/decisions/events.md.
"""

import os

from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.development")

app = Celery("jandrishti")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()


@app.task(bind=True, ignore_result=True)
def debug_task(self) -> str:
    return f"request: {self.request!r}"

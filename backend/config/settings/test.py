"""Test settings: in-memory database, eager Celery tasks, throttling disabled."""

from .base import *
from .base import REST_FRAMEWORK as _REST_FRAMEWORK

DEBUG = False
SECRET_KEY = "test-secret-key-not-used-anywhere-real"  # noqa: S105
ALLOWED_HOSTS = ["testserver", "localhost", "127.0.0.1"]
DATABASES = {"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": ":memory:"}}
CACHES = {"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}}
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]
CELERY_TASK_ALWAYS_EAGER = True

# Throttling stays wired up -- views name their scope explicitly, and removing
# the rates would make them raise instead of run. The limits are simply set
# high enough that no test trips them.
REST_FRAMEWORK = {
    **_REST_FRAMEWORK,
    "DEFAULT_THROTTLE_CLASSES": [],
    "DEFAULT_THROTTLE_RATES": {
        scope: "100000/min" for scope in _REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"]
    },
}
FUNDING_PAYMENTS_ENABLED = False
GOOGLE_CLIENT_ID = "test-google-client-id"

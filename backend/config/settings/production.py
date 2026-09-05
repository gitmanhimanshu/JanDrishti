"""
Production settings.

Refuses to start with a development secret, on SQLite, or without Redis. A
misconfigured deploy should fail loudly at boot rather than quietly serve an
insecure site.
"""

from django.core.exceptions import ImproperlyConfigured

from .base import *
from .base import DATABASES, SECRET_KEY, env, env_bool

DEBUG = False

if not SECRET_KEY or SECRET_KEY.startswith("insecure-"):
    raise ImproperlyConfigured("SECRET_KEY must be set to a strong random value in production.")
if not env("DATABASE_URL"):
    raise ImproperlyConfigured("DATABASE_URL (PostgreSQL) is required in production.")
if "postgresql" not in DATABASES["default"]["ENGINE"]:
    raise ImproperlyConfigured("Production must run on PostgreSQL.")
if not env("REDIS_URL"):
    raise ImproperlyConfigured("REDIS_URL is required in production (cache, throttling, Celery).")

SECURE_SSL_REDIRECT = env_bool("SECURE_SSL_REDIRECT", True)
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SESSION_COOKIE_SECURE = True
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"
CSRF_COOKIE_SECURE = True
CORS_ALLOW_ALL_ORIGINS = False

STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"},
}

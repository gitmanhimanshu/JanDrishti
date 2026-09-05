"""
Base settings shared by every environment.

Environment specific modules (development.py / production.py / test.py) import
from here and override only what genuinely differs. Nothing in this file reads
a secret with a usable default -- production refuses to boot without one.
"""

from __future__ import annotations

import os
from datetime import timedelta
from pathlib import Path

import dj_database_url
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent.parent
load_dotenv(BASE_DIR / ".env")


def env(key: str, default: str | None = None) -> str | None:
    return os.environ.get(key, default)


def env_bool(key: str, default: bool = False) -> bool:
    raw = os.environ.get(key)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def env_list(key: str, default: str = "") -> list[str]:
    return [item.strip() for item in os.environ.get(key, default).split(",") if item.strip()]


def env_int(key: str, default: int) -> int:
    try:
        return int(os.environ.get(key, default))
    except (TypeError, ValueError):
        return default


# ---------------------------------------------------------------------------
# Core
# ---------------------------------------------------------------------------
SECRET_KEY = env("SECRET_KEY", "insecure-development-key-do-not-use-in-production")
DEBUG = env_bool("DEBUG", False)
ALLOWED_HOSTS = env_list("ALLOWED_HOSTS", "localhost,127.0.0.1")
FRONTEND_URL = env("FRONTEND_URL", "http://localhost:3000")

DJANGO_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
]

THIRD_PARTY_APPS = [
    "rest_framework",
    "corsheaders",
    "django_filters",
    "drf_spectacular",
]

# Modular monolith. Each entry is an independently reasoned-about module with
# its own domain / application / infrastructure / api layers. Cross-module
# access goes through application services, never through the ORM of a peer.
LOCAL_APPS = [
    "jandrishti.shared",
    "jandrishti.modules.accounts",
    "jandrishti.modules.authentication",
    "jandrishti.modules.professional_verification",
    "jandrishti.modules.catalog",
    "jandrishti.modules.media",
    "jandrishti.modules.problems",
    "jandrishti.modules.experience",
    "jandrishti.modules.comments",
    "jandrishti.modules.social",
    "jandrishti.modules.issue_clustering",
    "jandrishti.modules.projects",
    "jandrishti.modules.funding",
    "jandrishti.modules.notifications",
    "jandrishti.modules.moderation",
    "jandrishti.modules.search",
    "jandrishti.modules.analytics",
    "jandrishti.modules.audit",
    "jandrishti.modules.government",
]

INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "jandrishti.shared.api.middleware.RequestContextMiddleware",
]

ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ]
        },
    }
]

# ---------------------------------------------------------------------------
# Database
# ---------------------------------------------------------------------------
# PostgreSQL is the production database (docs/decisions/database.md). SQLite is
# tolerated only as a zero-setup local fallback; no PostgreSQL-only column type
# is used anywhere in the schema, so both backends work.
_database_url = env("DATABASE_URL")
if _database_url:
    DATABASES = {
        "default": dj_database_url.parse(
            _database_url,
            conn_max_age=env_int("DB_CONN_MAX_AGE", 600),
            conn_health_checks=True,
        )
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
AUTH_USER_MODEL = "accounts.User"

# ---------------------------------------------------------------------------
# Cache / Redis
# ---------------------------------------------------------------------------
REDIS_URL = env("REDIS_URL")
if REDIS_URL:
    CACHES = {
        "default": {
            "BACKEND": "django_redis.cache.RedisCache",
            "LOCATION": REDIS_URL,
            "OPTIONS": {"CLIENT_CLASS": "django_redis.client.DefaultClient"},
        }
    }
else:
    CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
            "LOCATION": "jandrishti-local",
        }
    }

# ---------------------------------------------------------------------------
# Celery
# ---------------------------------------------------------------------------
CELERY_BROKER_URL = REDIS_URL or "memory://"
CELERY_RESULT_BACKEND = REDIS_URL or "cache+memory://"
CELERY_TASK_ALWAYS_EAGER = not bool(REDIS_URL)
CELERY_TASK_ACKS_LATE = True
CELERY_TASK_REJECT_ON_WORKER_LOST = True
CELERY_WORKER_PREFETCH_MULTIPLIER = 1
CELERY_TASK_TIME_LIMIT = 600
CELERY_TASK_SOFT_TIME_LIMIT = 540
CELERY_TIMEZONE = "Asia/Kolkata"

# ---------------------------------------------------------------------------
# DRF
# ---------------------------------------------------------------------------
REST_FRAMEWORK = {
    # Public-first: unauthenticated reads are the default and are explicitly
    # allowed. Write access is gated per-view by IsAuthenticated plus object
    # level permissions -- never by the frontend.
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.AllowAny"],
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "jandrishti.modules.authentication.api.authentication.JWTAuthentication",
    ],
    "DEFAULT_PAGINATION_CLASS": "jandrishti.shared.api.pagination.StandardPageNumberPagination",
    "PAGE_SIZE": 20,
    "DEFAULT_FILTER_BACKENDS": ["django_filters.rest_framework.DjangoFilterBackend"],
    "EXCEPTION_HANDLER": "jandrishti.shared.api.exception_handler.api_exception_handler",
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "DEFAULT_THROTTLE_CLASSES": [
        "rest_framework.throttling.AnonRateThrottle",
        "rest_framework.throttling.UserRateThrottle",
    ],
    "DEFAULT_THROTTLE_RATES": {
        "anon": "120/min",
        "user": "300/min",
        "auth": "20/min",
        "support": "60/min",
        "comment": "30/min",
        "create_problem": "10/hour",
        "create_experience": "10/hour",
        "upload": "60/hour",
        "verification": "5/day",
        "report": "20/hour",
    },
    "UNAUTHENTICATED_USER": "django.contrib.auth.models.AnonymousUser",
}

SPECTACULAR_SETTINGS = {
    "TITLE": "JanDrishti API",
    "DESCRIPTION": "Public-first civic intelligence and action platform.",
    "VERSION": "1.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
    "SCHEMA_PATH_PREFIX": "/api/v1",
}

# ---------------------------------------------------------------------------
# Auth / OAuth
# ---------------------------------------------------------------------------
GOOGLE_CLIENT_ID = env("GOOGLE_CLIENT_ID", "")
GOOGLE_CLIENT_SECRET = env("GOOGLE_CLIENT_SECRET", "")
GOOGLE_REDIRECT_URI = env("GOOGLE_REDIRECT_URI", f"{FRONTEND_URL}/auth/callback")

JWT_ALGORITHM = "HS256"
JWT_ISSUER = "jandrishti"
JWT_ACCESS_TTL = timedelta(minutes=env_int("JWT_ACCESS_TTL_MINUTES", 30))
JWT_REFRESH_TTL = timedelta(days=env_int("JWT_REFRESH_TTL_DAYS", 30))

# ---------------------------------------------------------------------------
# Media / uploads
# ---------------------------------------------------------------------------
CLOUDINARY_CLOUD_NAME = env("CLOUDINARY_CLOUD_NAME", "")
CLOUDINARY_API_KEY = env("CLOUDINARY_API_KEY", "")
CLOUDINARY_API_SECRET = env("CLOUDINARY_API_SECRET", "")

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "var" / "media"
STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "var" / "static"

# Server side upload validation. Frontend limits are a UX nicety; these are the
# limits that actually hold.
MAX_UPLOAD_SIZE_IMAGE = 10 * 1024 * 1024
MAX_UPLOAD_SIZE_VIDEO = 100 * 1024 * 1024
MAX_UPLOAD_SIZE_DOCUMENT = 20 * 1024 * 1024
ALLOWED_IMAGE_MIME_TYPES = ["image/jpeg", "image/png", "image/webp"]
ALLOWED_VIDEO_MIME_TYPES = ["video/mp4", "video/quicktime", "video/webm"]
ALLOWED_DOCUMENT_MIME_TYPES = ["application/pdf"]
FILE_UPLOAD_MAX_MEMORY_SIZE = 5 * 1024 * 1024

# ---------------------------------------------------------------------------
# Domain configuration
# ---------------------------------------------------------------------------
COMMENT_MAX_DEPTH = env_int("COMMENT_MAX_DEPTH", 5)
CLUSTERING_RADIUS_METRES = env_int("CLUSTERING_RADIUS_METRES", 150)
CLUSTERING_TITLE_SIMILARITY = 0.55
CLUSTERING_WINDOW_DAYS = env_int("CLUSTERING_WINDOW_DAYS", 180)
NEARBY_DEFAULT_RADIUS_KM = 5
TRENDING_HALF_LIFE_HOURS = 36

AI_PROVIDER = env("AI_PROVIDER", "null")
AI_API_KEY = env("AI_API_KEY", "")

# Real money movement stays off until the legal and payment architecture in
# docs/decisions/funding.md is actually in place.
FUNDING_PAYMENTS_ENABLED = env_bool("FUNDING_PAYMENTS_ENABLED", False)

# Sensitive-document retention for professional verification (docs/security.md).
VERIFICATION_DOCUMENT_RETENTION_DAYS = env_int("VERIFICATION_DOCUMENT_RETENTION_DAYS", 180)

# ---------------------------------------------------------------------------
# CORS / security
# ---------------------------------------------------------------------------
CORS_ALLOWED_ORIGINS = env_list("CORS_ALLOWED_ORIGINS", FRONTEND_URL or "")
CORS_ALLOW_CREDENTIALS = True
CSRF_TRUSTED_ORIGINS = CORS_ALLOWED_ORIGINS

SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = "strict-origin-when-cross-origin"
X_FRAME_OPTIONS = "DENY"

# ---------------------------------------------------------------------------
# i18n
# ---------------------------------------------------------------------------
LANGUAGE_CODE = "en-us"
TIME_ZONE = "Asia/Kolkata"
USE_I18N = True
USE_TZ = True

# ---------------------------------------------------------------------------
# Logging -- structured, and deliberately free of secrets.
# ---------------------------------------------------------------------------
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "filters": {"redact": {"()": "jandrishti.shared.infrastructure.logging.SecretRedactionFilter"}},
    "formatters": {
        "json": {"()": "jandrishti.shared.infrastructure.logging.JsonFormatter"},
        "simple": {"format": "%(levelname)s %(name)s %(message)s"},
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "simple" if DEBUG else "json",
            "filters": ["redact"],
        }
    },
    "root": {"handlers": ["console"], "level": env("LOG_LEVEL", "INFO")},
    "loggers": {
        "django.db.backends": {"level": "WARNING", "handlers": ["console"], "propagate": False},
        "jandrishti": {
            "level": env("LOG_LEVEL", "INFO"),
            "handlers": ["console"],
            "propagate": False,
        },
    },
}

"""Local development settings."""

from .base import *
from .base import env_list

DEBUG = True
ALLOWED_HOSTS = [*env_list("ALLOWED_HOSTS", "localhost,127.0.0.1,0.0.0.0"), "testserver"]
CORS_ALLOW_ALL_ORIGINS = True

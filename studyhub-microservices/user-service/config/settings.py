"""user-service (port 8000) - accounts, login (session-based) and profiles.
Owns its own database: DB_PATH (default data/users.db)
"""
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-change-me")
DEBUG = False
ALLOWED_HOSTS = ["*"]

INSTALLED_APPS = [
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "api",
]

MIDDLEWARE = [
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
]

# Sessions are shared across services via Redis, so a login on user-service is
# visible to room-service/message-service too. Falls back to a local in-memory
# cache (e.g. for unit tests) when REDIS_URL isn't set.
REDIS_URL = os.getenv("REDIS_URL")
CACHES = {
    "default": (
        {"BACKEND": "django.core.cache.backends.redis.RedisCache", "LOCATION": REDIS_URL}
        if REDIS_URL
        else {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}
    )
}
SESSION_ENGINE = "django.contrib.sessions.backends.cache"

ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"

DB_PATH = os.getenv("DB_PATH", str(BASE_DIR / "data" / "users.db"))
os.makedirs(os.path.dirname(DB_PATH) or ".", exist_ok=True)

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": DB_PATH,
    }
}

USE_TZ = True
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

"""room-service (port 8000) - chat rooms and topics.
Owns its own database: DB_PATH (default data/rooms.db)
Publishes "room_created" events to activity-service.
"""
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-change-me")
INTERNAL_KEY = os.getenv("INTERNAL_KEY", "internal-dev-key")
ACTIVITY_URL = os.getenv("ACTIVITY_URL", "http://127.0.0.1:8004")

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

# Shared with user-service via Redis, so a login there is visible here too.
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

DB_PATH = os.getenv("DB_PATH", str(BASE_DIR / "data" / "rooms.db"))
os.makedirs(os.path.dirname(DB_PATH) or ".", exist_ok=True)

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": DB_PATH,
    }
}

USE_TZ = True
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

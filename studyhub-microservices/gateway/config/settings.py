"""api-gateway (port 8000) - single entry point: routes /api/<resource>/... to the owning service,
aggregates health, rate-limits, and serves the web UI. It is stateless: no database, no sessions.
The shared login cookie is simply forwarded to the services (they read the Redis session).
"""
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-change-me")
DEBUG = False
ALLOWED_HOSTS = ["*"]

INSTALLED_APPS = ["api"]
MIDDLEWARE = ["django.middleware.common.CommonMiddleware"]
ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"
DATABASES = {}
APPEND_SLASH = False

SERVICES = {
    "user-service": os.getenv("USER_URL", "http://127.0.0.1:8001"),
    "room-service": os.getenv("ROOM_URL", "http://127.0.0.1:8002"),
    "message-service": os.getenv("MESSAGE_URL", "http://127.0.0.1:8003"),
    "activity-service": os.getenv("ACTIVITY_URL", "http://127.0.0.1:8004"),
    "notification-service": os.getenv("NOTIFICATION_URL", "http://127.0.0.1:8005"),
}

# first path segment after /api/  ->  owning service
ROUTES = {
    "auth": "user-service",
    "users": "user-service",
    "rooms": "room-service",
    "topics": "room-service",
    "messages": "message-service",
    "notifications": "notification-service",
    "activity": "activity-service",
}

RATE_LIMIT_PER_MINUTE = int(os.getenv("RATE_LIMIT_PER_MINUTE", "300"))
USE_TZ = True

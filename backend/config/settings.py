"""Django settings for the study app.

There is no database: documents are Markdown files (CONTENT_ROOT), state is CSV
(DATA_ROOT) and uploaded PDFs live in MEDIA_ROOT. See docs/ARCHITECTURE.md.
"""

from pathlib import Path

import environ

BASE_DIR = Path(__file__).resolve().parent.parent  # backend/
REPO_DIR = BASE_DIR.parent

env = environ.Env()
ENV_FILE = BASE_DIR / ".env"
if ENV_FILE.exists():
    env.read_env(str(ENV_FILE))

DEBUG = env.bool("DEBUG", default=False)
SECRET_KEY = env("SECRET_KEY", default="dev-insecure-secret-key-change-me" if DEBUG else None)
ALLOWED_HOSTS = env.list("ALLOWED_HOSTS", default=["localhost", "127.0.0.1"])
CSRF_TRUSTED_ORIGINS = env.list("CSRF_TRUSTED_ORIGINS", default=["http://localhost:3000"])

OWNER_PASSWORD_HASH = env("OWNER_PASSWORD_HASH", default="")

CONTENT_ROOT = Path(env("CONTENT_ROOT", default=str(REPO_DIR / "content")))
DATA_ROOT = Path(env("DATA_ROOT", default=str(REPO_DIR / "data")))
MEDIA_ROOT = Path(env("MEDIA_ROOT", default=str(REPO_DIR / "media")))
USE_X_ACCEL_REDIRECT = env.bool("USE_X_ACCEL_REDIRECT", default=False)

XP_FLASHCARD_CORRECT = env.int("XP_FLASHCARD_CORRECT", default=10)
XP_QUIZ_CORRECT = env.int("XP_QUIZ_CORRECT", default=10)
DEFAULT_PAGES_PER_DAY = env.int("DEFAULT_PAGES_PER_DAY", default=25)

INSTALLED_APPS = [
    "django.contrib.sessions",
    "rest_framework",
    "apps.core",
    "apps.materials",
    "apps.content",
    "apps.study",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

# No database at all.
DATABASES = {}

TEMPLATES = []

# Sessions live in a signed cookie, so no server-side session store is needed.
SESSION_ENGINE = "django.contrib.sessions.backends.signed_cookies"
SESSION_COOKIE_AGE = 60 * 60 * 24 * 30
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"
SESSION_COOKIE_SECURE = not DEBUG
CSRF_COOKIE_SAMESITE = "Lax"
CSRF_COOKIE_SECURE = not DEBUG
# The chapter PDF is shown in an iframe served from the same origin.
X_FRAME_OPTIONS = "SAMEORIGIN"

CACHES = {"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}}

PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.PBKDF2PasswordHasher",
]

LANGUAGE_CODE = "en-us"
TIME_ZONE = env("TIME_ZONE", default="Europe/Budapest")
USE_I18N = False
USE_TZ = True

# Large PDF uploads are streamed to a temp file; no hard size limit in Django.
FILE_UPLOAD_MAX_MEMORY_SIZE = 5 * 1024 * 1024
DATA_UPLOAD_MAX_MEMORY_SIZE = 20 * 1024 * 1024

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": ["apps.core.auth.OwnerSessionAuthentication"],
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.IsAuthenticated"],
    "UNAUTHENTICATED_USER": None,
    "UNAUTHENTICATED_TOKEN": None,
    "DEFAULT_RENDERER_CLASSES": ["rest_framework.renderers.JSONRenderer"],
    "DEFAULT_PARSER_CLASSES": [
        "rest_framework.parsers.JSONParser",
        "rest_framework.parsers.MultiPartParser",
    ],
    "DEFAULT_THROTTLE_RATES": {"login": "10/min"},
    "EXCEPTION_HANDLER": "apps.core.exceptions.exception_handler",
}

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {"console": {"class": "logging.StreamHandler"}},
    "root": {"handlers": ["console"], "level": "INFO"},
}

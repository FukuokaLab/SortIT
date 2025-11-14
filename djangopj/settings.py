"""
Django settings for djangopj project.

For more information on this file, see
https://docs.djangoproject.com/en/4.2/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/4.2/ref/settings/
"""

from pathlib import Path
import os

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# Quick-start development settings - unsuitable for production

DEBUG = "True"
SECRET_KEY = "hellofriend!"
ALLOWED_HOSTS = ["localhost", "df1", "100.123.110.99"]

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
        },
        "file": {
            "level": "DEBUG",
            "class": "logging.FileHandler",
            "filename": "logs/test.log",
        },
    },
    "root": {
        "handlers": ["console"],
        "level": "WARNING",
    },
}
# Application definition

INSTALLED_APPS = [
    "sortIT.apps.SortITConfig",
    "account.apps.AccountConfig",
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "widget_tweaks",
    "admin_thumbnails",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "djangopj.urls"

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
            ],
        },
    },
]

WSGI_APPLICATION = "djangopj.wsgi.application"

# Database
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
        "USER": "postgres",
        "PASSWORD": "pass_for_db",
        "HOST": "db",
        "PORT": 5432,
    }
}

# Password validation

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]


# Internationalization, Locale
LANGUAGE_CODE = "en"
TIME_ZONE = "Asia/Tokyo"
USE_I18N = True
USE_TZ = False

# Static files (CSS, JavaScript, Images)
STATIC_URL = "/static/"

if DEBUG:
    STATICFILES_DIRS = [
        os.path.join(BASE_DIR, "assets"),
        os.path.join(BASE_DIR, "static"),
    ]
else:
    STATIC_ROOT = os.path.join(BASE_DIR, "static")


# Default primary key field type
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
MEDIA_ROOT = BASE_DIR.joinpath("media")

MEDIA_URL = "/media/"

LOGIN_URL = "account:login"
LOGOUT_REDIRECT_URL = "account:login"
LOGIN_REDIRECT_URL = "sortIT:choose_proj"

CSRF_COOKIE_SECURE = False  # turn on when use https only
CSRF_COOKIE_HTTPONLY = True

DATA_UPLOAD_MAX_NUMBER_FILES = 50000
DATA_UPLOAD_MAX_NUMBER_FIELDS = 50000

host_name = os.getenv("SERVER_NAME")
CSRF_TRUSTED_ORIGINS = [f"https://{host_name}", f"http://{host_name}"]

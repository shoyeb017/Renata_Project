"""
Django settings for shift_analytics project.
"""
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.environ.get(
    "DJANGO_SECRET_KEY",
    "django-insecure-lbrbhyevme4s3&&t#!l-%-i8x=!2qe&m=zc^i&m=h&)$hx+^jg",
)

DEBUG = os.environ.get("DJANGO_DEBUG", "True") == "True"

ALLOWED_HOSTS = os.environ.get("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1").split(",")

INSTALLED_APPS = [
    "unfold",
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'rest_framework',
    'corsheaders',
    'config_app',
    'shifts',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'shift_analytics.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'shift_analytics.wsgi.application'

# Database
# Defaults to SQLite for simple/local deployment. Set DATABASE_URL (e.g.
# postgres://user:pass@host:5432/dbname) to switch to PostgreSQL without
# any code changes - see README "Database setup".
DATABASE_URL = os.environ.get("DATABASE_URL")

if DATABASE_URL and DATABASE_URL.startswith("postgres"):
    import re
    match = re.match(
        r"postgres(?:ql)?://(?P<user>[^:]+):(?P<password>[^@]*)@(?P<host>[^:/]+):?(?P<port>\d*)/(?P<name>.+)",
        DATABASE_URL,
    )
    if not match:
        raise ValueError("DATABASE_URL is set but could not be parsed. Expected postgres://user:pass@host:port/dbname")
    g = match.groupdict()
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': g['name'],
            'USER': g['user'],
            'PASSWORD': g['password'],
            'HOST': g['host'],
            'PORT': g['port'] or '5432',
        }
    }
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

STATIC_URL = 'static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# REST Framework
REST_FRAMEWORK = {
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 200,
}

# CORS - the React dev server runs on a different port, so it needs to be
# allowed to call this API during local development.
CORS_ALLOWED_ORIGINS = os.environ.get(
    "CORS_ALLOWED_ORIGINS",
    "http://localhost:5173,http://127.0.0.1:5173",
).split(",")

# Path to the source dataset CSV. Override via env var to point at a
# different dataset without touching any code - see README "Swappable dataset".
DATASET_PATH = os.environ.get("DATASET_PATH", str(BASE_DIR / "data" / "shift_data.csv"))

UNFOLD = {
    "SITE_TITLE": "Renata Admin",
    "SITE_HEADER": "Renata Shift Analytics",
    "SITE_SYMBOL": "dashboard",
}
from datetime import timedelta
import os
from pathlib import Path

import pymysql
from django.core.exceptions import ImproperlyConfigured
from dotenv import load_dotenv

pymysql.install_as_MySQLdb()

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / '.env')

USE_SQLITE = os.getenv('USE_SQLITE', 'True').strip().lower() == 'true'
MYSQL_DB_NAME = os.getenv('DB_NAME')
MYSQL_DB_USER = os.getenv('DB_USER')
MYSQL_DB_PASSWORD = os.getenv('DB_PASSWORD')
MYSQL_DB_HOST = os.getenv('DB_HOST')
MYSQL_DB_PORT = os.getenv('DB_PORT')

IS_RENDER = os.getenv('RENDER', '').strip().lower() == 'true'
if IS_RENDER and USE_SQLITE:
    raise ImproperlyConfigured(
        'USE_SQLITE must be False when running on Render; configure the '
        'production MySQL environment variables.'
    )

DEBUG = os.getenv('DEBUG', 'False' if IS_RENDER else 'True').strip().lower() == 'true'
if IS_RENDER and DEBUG:
    raise ImproperlyConfigured('DEBUG must be False when running on Render.')

SECRET_KEY = os.getenv('DJANGO_SECRET_KEY')
if not SECRET_KEY:
    if DEBUG:
        SECRET_KEY = 'django-insecure-change-me'
    else:
        raise ImproperlyConfigured('DJANGO_SECRET_KEY must be set when DEBUG is False.')
elif not DEBUG and SECRET_KEY in {
    'change-me-in-production',
    'django-insecure-change-me',
}:
    raise ImproperlyConfigured(
        'Set DJANGO_SECRET_KEY to a unique secret when DEBUG is False.'
    )

ALLOWED_HOSTS = [
    host.strip()
    for host in os.getenv(
        'ALLOWED_HOSTS',
        'localhost,127.0.0.1,0.0.0.0,testserver' if DEBUG else ''
    ).split(',')
    if host.strip()
]
RENDER_EXTERNAL_HOSTNAME = os.getenv('RENDER_EXTERNAL_HOSTNAME', '').strip()
if RENDER_EXTERNAL_HOSTNAME and RENDER_EXTERNAL_HOSTNAME not in ALLOWED_HOSTS:
    ALLOWED_HOSTS.append(RENDER_EXTERNAL_HOSTNAME)
if not DEBUG and not ALLOWED_HOSTS:
    raise ImproperlyConfigured('ALLOWED_HOSTS must be set when DEBUG is False.')
if not DEBUG and '*' in ALLOWED_HOSTS:
    raise ImproperlyConfigured('ALLOWED_HOSTS must not contain "*" when DEBUG is False.')

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'corsheaders',
    'rest_framework',
    'rest_framework_simplejwt',
    'rest_framework_simplejwt.token_blacklist',
    'accounts',
    'academics',
    'courses',
    'users',
]

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]


ROOT_URLCONF = 'config.urls'

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

WSGI_APPLICATION = 'config.wsgi.application'

if USE_SQLITE:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }
else:
    mysql_settings = {
        'DB_NAME': MYSQL_DB_NAME,
        'DB_USER': MYSQL_DB_USER,
        'DB_PASSWORD': MYSQL_DB_PASSWORD,
        'DB_HOST': MYSQL_DB_HOST,
        'DB_PORT': MYSQL_DB_PORT,
    }
    missing_mysql_settings = [
        name for name, value in mysql_settings.items() if not value
    ]
    if missing_mysql_settings:
        raise ImproperlyConfigured(
            'MySQL is enabled (USE_SQLITE=False), but these settings are '
            f'missing: {", ".join(missing_mysql_settings)}.'
        )

    mysql_ssl_ca = Path(
        os.getenv('MYSQL_SSL_CA', str(BASE_DIR / 'certs' / 'ca.pem'))
    )
    if not mysql_ssl_ca.is_absolute():
        mysql_ssl_ca = BASE_DIR / mysql_ssl_ca
    if not mysql_ssl_ca.is_file():
        raise ImproperlyConfigured(
            f'MySQL SSL CA certificate not found at {mysql_ssl_ca}. '
            'Set MYSQL_SSL_CA to the certificate file path.'
        )

    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.mysql',
            'NAME': MYSQL_DB_NAME,
            'USER': MYSQL_DB_USER,
            'PASSWORD': MYSQL_DB_PASSWORD,
            'HOST': MYSQL_DB_HOST,
            'PORT': MYSQL_DB_PORT,
            'OPTIONS': {
                'charset': 'utf8mb4',
                'ssl_ca': str(mysql_ssl_ca),
                'ssl_verify_cert': True,
                'ssl_verify_identity': True,
            },
        }
    }

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator', 'OPTIONS': {'min_length': 8}},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LANGUAGE_CODE = 'fr-fr'
TIME_ZONE = 'Europe/Paris'
USE_I18N = True
USE_TZ = True

STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
MEDIA_URL = '/media/'
MEDIA_ROOT = Path(os.getenv('MEDIA_ROOT', str(BASE_DIR / 'media')))
if not MEDIA_ROOT.is_absolute():
    MEDIA_ROOT = BASE_DIR / MEDIA_ROOT

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
AUTH_USER_MODEL = 'accounts.User'

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
}

SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=60),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True,
}

FRONTEND_URL = os.getenv('FRONTEND_URL', '').strip().rstrip('/')
DEFAULT_FRONTEND_ORIGINS = (
    'http://localhost:5173,http://127.0.0.1:5173'
    if DEBUG
    else FRONTEND_URL
)

CORS_ALLOWED_ORIGINS = [
    origin.strip()
    for origin in (
        os.getenv('CORS_ALLOWED_ORIGINS', '').strip()
        or DEFAULT_FRONTEND_ORIGINS
    ).split(',')
    if origin.strip()
]

CORS_ALLOW_CREDENTIALS = True

CSRF_TRUSTED_ORIGINS = [
    origin.strip()
    for origin in (
        os.getenv('CSRF_TRUSTED_ORIGINS', '').strip()
        or DEFAULT_FRONTEND_ORIGINS
    ).split(',')
    if origin.strip()
]

SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
SECURE_SSL_REDIRECT = not DEBUG
SECURE_HSTS_SECONDS = 3600 if not DEBUG else 0
SESSION_COOKIE_SECURE = not DEBUG
CSRF_COOKIE_SECURE = not DEBUG

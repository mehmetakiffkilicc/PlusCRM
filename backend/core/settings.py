import os
from pathlib import Path
from decouple import Config, RepositoryEnv, config as default_config

BASE_DIR = Path(__file__).resolve().parent.parent

# Load .env explicitly from the project root
env_path = BASE_DIR.parent / '.env'
if env_path.exists():
    config = Config(RepositoryEnv(str(env_path)))
else:
    config = default_config

SECRET_KEY = config('SECRET_KEY', default='django-insecure-dev-key-CHANGE-IN-PRODUCTION')
DEBUG = config('DEBUG', default=False, cast=bool)
_allowed = config('ALLOWED_HOSTS', default='localhost,127.0.0.1').split(',')
ALLOWED_HOSTS = [h.strip() for h in _allowed if h.strip()] or ['localhost', '127.0.0.1']

# Railway health check ve platform hostları
_railway_hosts = [
    'healthcheck.railway.app',
]
for _env_var in ('RAILWAY_PUBLIC_DOMAIN', 'RAILWAY_PRIVATE_DOMAIN', 'RAILWAY_STATIC_URL'):
    _val = os.environ.get(_env_var, '').strip()
    if _val and _val not in ALLOWED_HOSTS:
        _railway_hosts.append(_val)

for _h in _railway_hosts:
    if _h and _h not in ALLOWED_HOSTS:
        ALLOWED_HOSTS.append(_h)

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'rest_framework',
    'corsheaders',
    'api.apps.ApiConfig',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.middleware.gzip.GZipMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'core.middleware.SecurityHeadersMiddleware',
]

ROOT_URLCONF = 'core.urls'

# Django URL configuration
APPEND_SLASH = True

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'core.wsgi.application'

# Database
import dj_database_url

_db_url = config('DATABASE_URL', default=config('POSTGRES_URL', default=f"sqlite:///{BASE_DIR / config('DB_NAME', default='db.sqlite3')}"))
# Railway sometimes provides postgres:// instead of postgresql://
if _db_url.startswith('postgres://'):
    _db_url = _db_url.replace('postgres://', 'postgresql://', 1)
DATABASES = {
    'default': dj_database_url.parse(_db_url, conn_max_age=600, conn_health_checks=True)
}

# PostgreSQL bellek parametreleri — her session'da SET olarak uygulanır
# work_mem: sıralama/hash işlemleri için sorgu başına max RAM
#   Önceki: 32MB → 10 conn × 3 worker × 32MB = ~960MB peak (Railway maliyet kaynağı)
#   Şimdi: 8MB → ~240MB peak. Çok büyük JOIN'ler temp_file_limit'e taşar (kabul edilebilir).
# maintenance_work_mem: VACUUM/index build için (sadece gece bakım — düşük tutmak güvenli)
# effective_cache_size: sorgu planlayıcısına cache büyüklüğü ipucu (gerçek RAM tüketmez)
# temp_file_limit: geçici dosya boyutu sınırı (RAM taşmasını diske yönlendirir)
if 'postgresql' in _db_url:
    DATABASES['default'].setdefault('OPTIONS', {})
    DATABASES['default']['OPTIONS']['options'] = (
        '-c work_mem=8MB '
        '-c maintenance_work_mem=64MB '
        '-c effective_cache_size=1GB '
        '-c temp_file_limit=1024MB '
        '-c statement_timeout=300000 '
        '-c idle_in_transaction_session_timeout=60000'
    )

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# Cache — Redis varsa kullan, yoksa DatabaseCache (multi-worker güvenli)
_redis_url = config('REDIS_URL', default='')
if _redis_url:
    CACHES = {
        'default': {
            'BACKEND': 'django.core.cache.backends.redis.RedisCache',
            'LOCATION': _redis_url,
        }
    }
else:
    CACHES = {
        'default': {
            'BACKEND': 'django.core.cache.backends.db.DatabaseCache',
            'LOCATION': 'django_cache',
        }
    }

LANGUAGE_CODE = 'tr-TR'
TIME_ZONE = 'Europe/Istanbul'
USE_I18N = True
USE_TZ = True

STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Static files storage — use STORAGES dict (Django 4.2+ compatible, avoids deprecation)
# STATICFILES_STORAGE is deprecated in Django 5.1 and removed in Django 6.0
import django
_django_version = tuple(int(x) for x in django.VERSION[:2])
if _django_version >= (4, 2):
    STORAGES = {
        "default": {
            "BACKEND": "django.core.files.storage.FileSystemStorage",
        },
        "staticfiles": {
            "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
        },
    }
else:
    STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# Security Headers (BUG-v2-007)
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'
SECURE_BROWSER_XSS_FILTER = True
if not DEBUG:
    SECURE_HSTS_SECONDS = 31536000
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True

# CORS Settings
CORS_ALLOW_ALL_ORIGINS = config('CORS_ALLOW_ALL', default=False, cast=bool) # Sadece DEBUG veya özel durumlar için
CORS_ALLOWED_ORIGINS = config('CORS_ALLOWED_ORIGINS', 
    default='http://localhost:3000,http://localhost:3001,http://127.0.0.1:3000,https://show.xpluscrm.com'
).split(',')
CORS_ALLOW_CREDENTIALS = True
CSRF_TRUSTED_ORIGINS = config('CSRF_TRUSTED_ORIGINS', default='http://localhost:3000,http://localhost:3001,https://*.up.railway.app,https://show.xpluscrm.com').split(',')

# REST Framework
NUM_PROXIES = 1  # Railway reverse proxy — throttle için gerçek IP'yi X-Forwarded-For'dan al

REST_FRAMEWORK = {
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',  # Require authentication by default
    ],
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'api.authentication.JWTAuthentication',  # Custom JWT authentication
    ],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 100,
    'DEFAULT_THROTTLE_CLASSES': [
        'rest_framework.throttling.AnonRateThrottle',
        'rest_framework.throttling.UserRateThrottle',
        'rest_framework.throttling.ScopedRateThrottle',
    ],
    'DEFAULT_THROTTLE_RATES': {
        'anon': config('THROTTLE_ANON', default='100/hour'),
        'user': config('THROTTLE_USER', default='1000/hour'),
        'login': config('THROTTLE_LOGIN', default='5/minute')
    }
}

# JWT Settings
JWT_SECRET = config('JWT_SECRET', default='your-jwt-secret-key')
JWT_ALGORITHM = config('JWT_ALGORITHM', default='HS256')
JWT_EXPIRY_HOURS = config('JWT_EXPIRY_HOURS', default=168, cast=int)

# Logging Configuration
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
        'simple': {
            'format': '{levelname} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'level': 'DEBUG' if DEBUG else 'INFO',
            'class': 'logging.StreamHandler',
            'formatter': 'verbose' if DEBUG else 'simple',
        },

    },
    'loggers': {
        'django': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
        'api': {
            'handlers': ['console'],
            'level': 'DEBUG' if DEBUG else 'INFO',
            'propagate': False,
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'INFO',
    },
}

# Add file logging only in local DEBUG mode
if DEBUG:
    os.makedirs(BASE_DIR / 'logs', exist_ok=True)
    LOGGING['handlers']['file'] = {
        'level': 'INFO',
        'class': 'logging.handlers.RotatingFileHandler',
        'filename': BASE_DIR / 'logs' / 'django.log',
        'maxBytes': 10 * 1024 * 1024,
        'backupCount': 5,
        'formatter': 'verbose',
    }
    LOGGING['handlers']['api_file'] = {
        'level': 'DEBUG',
        'class': 'logging.handlers.RotatingFileHandler',
        'filename': BASE_DIR / 'logs' / 'api.log',
        'maxBytes': 10 * 1024 * 1024,
        'backupCount': 10,
        'formatter': 'verbose',
    }
    LOGGING['loggers']['django']['handlers'].append('file')
    LOGGING['loggers']['api']['handlers'] = ['api_file', 'console']

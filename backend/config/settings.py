
"""Pengaturan Django untuk SIMONTA. Nilai sensitif dibaca dari environment."""
from datetime import timedelta
from pathlib import Path

from celery.schedules import crontab
from django.core.exceptions import ImproperlyConfigured

import environ


BASE_DIR = Path(__file__).resolve().parent.parent

env = environ.Env(
    DEBUG=(bool, False),
    ALLOWED_HOSTS=(list, ["localhost", "127.0.0.1"]),
    CORS_ALLOWED_ORIGINS=(list, ["http://localhost:5173"]),
    CSRF_TRUSTED_ORIGINS=(list, ["http://localhost:5173"]),
)

environ.Env.read_env(BASE_DIR / ".env")

# --- Deteksi lingkungan ---
IS_VERCEL = env.bool("VERCEL", default=False)

SECRET_KEY = env("SECRET_KEY")
DEBUG = env.bool("DEBUG", default=False)

if IS_VERCEL and DEBUG:
    raise ImproperlyConfigured(
        "DEBUG harus False ketika SIMONTA dijalankan di Vercel."
    )

# --- Host aplikasi ---
_DEFAULT_ALLOWED_HOSTS = (
    [] if IS_VERCEL else ["localhost", "127.0.0.1"]
)

ALLOWED_HOSTS = env.list(
    "ALLOWED_HOSTS",
    default=_DEFAULT_ALLOWED_HOSTS,
)

# Vercel menyediakan hostname deployment dan domain production.
# System environment variables harus diaktifkan di dashboard Vercel.
VERCEL_HOSTS = []

for variable_name in (
    "VERCEL_URL",
    "VERCEL_BRANCH_URL",
    "VERCEL_PROJECT_PRODUCTION_URL",
):
    hostname = env(variable_name, default="").strip()
    if hostname and hostname not in VERCEL_HOSTS:
        VERCEL_HOSTS.append(hostname)

for hostname in VERCEL_HOSTS:
    if hostname not in ALLOWED_HOSTS:
        ALLOWED_HOSTS.append(hostname)

if IS_VERCEL and not ALLOWED_HOSTS:
    raise ImproperlyConfigured(
        "ALLOWED_HOSTS belum dikonfigurasi. "
        "Aktifkan Vercel System Environment Variables "
        "atau atur ALLOWED_HOSTS."
    )

# Domain Vercel otomatis menjadi origin HTTPS.
VERCEL_ORIGINS = [
    f"https://{hostname}"
    for hostname in VERCEL_HOSTS
]

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # Pihak ketiga
    "rest_framework",
    "drf_spectacular",
    "corsheaders",
    "axes",
    # Aplikasi proyek
    "core",
    "accounts",
    "audit",
    "akademik",
    "notifikasi",
    "milestone",
    "dokumen",
    "review",
    "dashboard",
    "jadwal",
    "pesan",
    "keterlambatan",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "axes.middleware.AxesMiddleware",  # harus paling akhir
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

# --- Basis data: MySQL 8 ---
# Pada Vercel, seluruh kredensial database wajib berasal dari environment.
# Pada development lokal, nilai default Laragon tetap dipertahankan.
if IS_VERCEL:
    REQUIRED_DATABASE_ENV = (
        "DB_NAME",
        "DB_USER",
        "DB_PASSWORD",
        "DB_HOST",
        "DB_PORT",
    )

    missing_database_env = [
        name
        for name in REQUIRED_DATABASE_ENV
        if not env(name, default="").strip()
    ]

    if missing_database_env:
        raise ImproperlyConfigured(
            "Environment database belum lengkap: "
            + ", ".join(missing_database_env)
        )

    DATABASE_CONFIG = {
        "NAME": env("DB_NAME"),
        "USER": env("DB_USER"),
        "PASSWORD": env("DB_PASSWORD"),
        "HOST": env("DB_HOST"),
        "PORT": env("DB_PORT"),
    }
else:
    DATABASE_CONFIG = {
        "NAME": env("DB_NAME", default="simonta"),
        "USER": env("DB_USER", default="root"),
        "PASSWORD": env("DB_PASSWORD", default=""),
        "HOST": env("DB_HOST", default="127.0.0.1"),
        "PORT": env("DB_PORT", default="3306"),
    }

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.mysql",
        **DATABASE_CONFIG,
        # Function serverless tidak mengandalkan koneksi persisten
        # antar-invocation.
        "CONN_MAX_AGE": 0,
        "OPTIONS": {
            "charset": "utf8mb4",
            "init_command": "SET sql_mode='STRICT_TRANS_TABLES'",
        },
        "TEST": {
            "CHARSET": "utf8mb4",
            "COLLATION": "utf8mb4_unicode_ci",
        },
    }
}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# --- Autentikasi dan password ---
AUTH_USER_MODEL = "accounts.User"

PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.Argon2PasswordHasher",  # utama
    "django.contrib.auth.hashers.PBKDF2PasswordHasher",  # cadangan verifikasi hash lama
]

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

AUTHENTICATION_BACKENDS = [
    "axes.backends.AxesStandaloneBackend",  # harus pertama
    "django.contrib.auth.backends.ModelBackend",
]

# django-axes: 5 kali gagal per 15 menit per kombinasi akun + IP
AXES_FAILURE_LIMIT = 5
AXES_COOLOFF_TIME = timedelta(minutes=15)
AXES_LOCKOUT_PARAMETERS = [["username", "ip_address"]]
AXES_RESET_ON_SUCCESS = True
AXES_LOCKOUT_CALLABLE = "accounts.lockout.lockout_response"
AXES_USERNAME_FORM_FIELD = "username"

# --- Sesi dan cookie ---
SESSION_COOKIE_AGE = 14 * 24 * 60 * 60
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"
SESSION_COOKIE_SECURE = not DEBUG

# Frontend perlu membaca cookie CSRF untuk header X-CSRFToken.
CSRF_COOKIE_HTTPONLY = False
CSRF_COOKIE_SAMESITE = "Lax"
CSRF_COOKIE_SECURE = not DEBUG

# Vercel berada di belakang reverse proxy HTTPS.
# Header ini memungkinkan Django mengenali request HTTPS asli.
if IS_VERCEL:
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

# --- Lokalisasi ---
LANGUAGE_CODE = "id"
TIME_ZONE = "Asia/Jakarta"
USE_I18N = True
USE_TZ = True

# --- Berkas statis dan unggahan ---
STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

# Sementara tetap menggunakan penyimpanan lokal.
# Produksi memerlukan object storage persisten untuk unggahan pengguna.
MEDIA_ROOT = BASE_DIR / "media"

# Masa berlaku tautan unduh berkas (BR-09), dalam detik.
UNDUH_TOKEN_MAX_AGE = 15 * 60

# --- CORS dan CSRF ---
_DEFAULT_LOCAL_ORIGINS = (
    ["http://localhost:5173"] if DEBUG else []
)

CORS_ALLOWED_ORIGINS = env.list(
    "CORS_ALLOWED_ORIGINS",
    default=_DEFAULT_LOCAL_ORIGINS,
)

CSRF_TRUSTED_ORIGINS = env.list(
    "CSRF_TRUSTED_ORIGINS",
    default=_DEFAULT_LOCAL_ORIGINS,
)

for origin in VERCEL_ORIGINS:
    if origin not in CORS_ALLOWED_ORIGINS:
        CORS_ALLOWED_ORIGINS.append(origin)

    if origin not in CSRF_TRUSTED_ORIGINS:
        CSRF_TRUSTED_ORIGINS.append(origin)

CORS_ALLOW_CREDENTIALS = True

# --- Django REST Framework ---
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework.authentication.SessionAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    "DEFAULT_RENDERER_CLASSES": [
        "rest_framework.renderers.JSONRenderer",
    ],
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
}

SPECTACULAR_SETTINGS = {
    "TITLE": "SIMONTA API",
    "DESCRIPTION": "Sistem Monitoring Tugas Akhir, Prodi Sistem Informasi UIN Raden Intan Lampung.",
    "VERSION": "1.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
}

# --- Email: console untuk development, SMTP untuk production ---
EMAIL_BACKEND = env(
    "EMAIL_BACKEND",
    default=(
        "django.core.mail.backends.console.EmailBackend"
        if DEBUG
        else "django.core.mail.backends.smtp.EmailBackend"
    ),
)

EMAIL_HOST = env("EMAIL_HOST", default="localhost")
EMAIL_PORT = env.int("EMAIL_PORT", default=587)
EMAIL_HOST_USER = env("EMAIL_HOST_USER", default="")
EMAIL_HOST_PASSWORD = env("EMAIL_HOST_PASSWORD", default="")
EMAIL_USE_TLS = env.bool("EMAIL_USE_TLS", default=True)
EMAIL_USE_SSL = env.bool("EMAIL_USE_SSL", default=False)
DEFAULT_FROM_EMAIL = env(
    "DEFAULT_FROM_EMAIL",
    default="SIMONTA <no-reply@simonta.local>",
)

# URL frontend digunakan untuk tautan dalam email.
# Di Vercel, gunakan domain production sebagai default.
DEFAULT_FRONTEND_BASE_URL = (
    f"https://{env('VERCEL_PROJECT_PRODUCTION_URL')}"
    if IS_VERCEL and env("VERCEL_PROJECT_PRODUCTION_URL", default="")
    else "http://localhost:5173"
)

FRONTEND_BASE_URL = env(
    "FRONTEND_BASE_URL",
    default=DEFAULT_FRONTEND_BASE_URL,
).rstrip("/")

# --- Celery + Redis (T2.3) ---
CELERY_BROKER_URL = env(
    "CELERY_BROKER_URL",
    default="redis://127.0.0.1:6379/0",
)

CELERY_RESULT_BACKEND = env(
    "CELERY_RESULT_BACKEND",
    default="redis://127.0.0.1:6379/1",
)

CELERY_TASK_IGNORE_RESULT = True
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_TIMEZONE = TIME_ZONE
CELERY_ENABLE_UTC = True

CELERY_BEAT_SCHEDULE = {
    "proses-pengingat-jatuh-tempo-setiap-menit": {
        "task": "notifikasi.kirim_pengingat_jatuh_tempo",
        "schedule": 60.0,
    },
    "peringatan-tenggat-setiap-hari-wib": {
        "task": "notifikasi.kirim_peringatan_tenggat",
        "schedule": crontab(hour=0, minute=10),
    },
    "rekonsiliasi-pengingat-harian": {
        "task": "notifikasi.hitung_ulang_semua_pengingat",
        "schedule": crontab(hour=1, minute=10),
    },
    "ringkasan-mingguan-senin-wib": {
        "task": "notifikasi.kirim_ringkasan_mingguan",
        "schedule": crontab(day_of_week="mon", hour=8, minute=0),
    },
    "proses-keterlambatan-harian": {
        "task": "keterlambatan.proses_keterlambatan_harian",
        "schedule": crontab(hour=0, minute=20),
    },
}

"""Pengaturan Django untuk SIMONTA. Nilai sensitif dibaca dari backend/.env."""
from datetime import timedelta
from pathlib import Path

from celery.schedules import crontab

import environ

BASE_DIR = Path(__file__).resolve().parent.parent

env = environ.Env(
    DEBUG=(bool, False),
    ALLOWED_HOSTS=(list, ["localhost", "127.0.0.1"]),
    CORS_ALLOWED_ORIGINS=(list, ["http://localhost:5173"]),
    CSRF_TRUSTED_ORIGINS=(list, ["http://localhost:5173"]),
)
environ.Env.read_env(BASE_DIR / ".env")

SECRET_KEY = env("SECRET_KEY")
DEBUG = env("DEBUG")
ALLOWED_HOSTS = env("ALLOWED_HOSTS")

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

# --- Basis data: MySQL 8 (Laragon), utf8mb4 ---
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.mysql",
        "NAME": env("DB_NAME", default="simonta"),
        "USER": env("DB_USER", default="root"),
        "PASSWORD": env("DB_PASSWORD", default=""),
        "HOST": env("DB_HOST", default="127.0.0.1"),
        "PORT": env("DB_PORT", default="3306"),
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
AXES_LOCKOUT_CALLABLE = "accounts.lockout.lockout_response"  # respons JSON 429
# Wajib: tanpa ini axes memakai USERNAME_FIELD ("identifier") sebagai kunci kredensial,
# padahal login API dan form Django admin mengirim kunci "username".
AXES_USERNAME_FORM_FIELD = "username"

# --- Sesi dan cookie ---
# SESSION_COOKIE_AGE = masa sesi "ingat saya" (14 hari). Tanpa "ingat saya",
# view login membuat sesi berakhir saat browser ditutup.
SESSION_COOKIE_AGE = 14 * 24 * 60 * 60
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"
SESSION_COOKIE_SECURE = not DEBUG
CSRF_COOKIE_HTTPONLY = False  # frontend perlu membaca token untuk header X-CSRFToken
CSRF_COOKIE_SAMESITE = "Lax"
CSRF_COOKIE_SECURE = not DEBUG

# --- Lokalisasi ---
LANGUAGE_CODE = "id"
TIME_ZONE = "Asia/Jakarta"
USE_I18N = True
USE_TZ = True

# --- Berkas statis dan unggahan ---
STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
MEDIA_ROOT = BASE_DIR / "media"  # privat; tidak disajikan sebagai URL publik (tidak ada rute /media/)
# Masa berlaku tautan unduh berkas (BR-09), dalam detik.
UNDUH_TOKEN_MAX_AGE = 15 * 60

# --- CORS dan CSRF (frontend Vite) ---
CORS_ALLOWED_ORIGINS = env("CORS_ALLOWED_ORIGINS")
CORS_ALLOW_CREDENTIALS = True
CSRF_TRUSTED_ORIGINS = env("CSRF_TRUSTED_ORIGINS")

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
DEFAULT_FROM_EMAIL = env("DEFAULT_FROM_EMAIL", default="SIMONTA <no-reply@simonta.local>")
FRONTEND_BASE_URL = env("FRONTEND_BASE_URL", default="http://localhost:5173")

# --- Celery + Redis (T2.3) ---
CELERY_BROKER_URL = env("CELERY_BROKER_URL", default="redis://127.0.0.1:6379/0")
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

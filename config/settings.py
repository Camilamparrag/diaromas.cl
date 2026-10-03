"""
Configuración de Django para Diaromas.

Todo lo configurable (secretos, base de datos, datos del negocio) se lee desde
variables de entorno con valores por defecto pensados para desarrollo.
"""

import os
from decimal import Decimal
from pathlib import Path

import dj_database_url
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent

# Lee el .env de la raíz del proyecto (no falla si no existe)
load_dotenv(BASE_DIR / ".env")


# --- Utilidades -------------------------------------------------------------
def env(name: str, default: str = "") -> str:
    value = os.environ.get(name)
    return default if value is None or value == "" else value


def env_bool(name: str, default: bool = False) -> bool:
    value = os.environ.get(name)
    if value is None or value == "":
        return default
    return value.strip().lower() in {"1", "true", "yes", "on", "si", "sí"}


def env_list(name: str, default: str = "") -> list[str]:
    raw = env(name, default)
    return [item.strip() for item in raw.split(",") if item.strip()]


# --- Seguridad --------------------------------------------------------------
SECRET_KEY = env(
    "DJANGO_SECRET_KEY",
    "django-insecure-clave-de-desarrollo-cambia-en-produccion-diaromas",
)

DEBUG = env_bool("DJANGO_DEBUG", True)

ALLOWED_HOSTS = env_list("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1,[::1]")

CSRF_TRUSTED_ORIGINS = env_list(
    "CSRF_TRUSTED_ORIGINS",
    "http://localhost:8000,https://localhost:8000,http://127.0.0.1:8000,https://127.0.0.1:8000,http://localhost:8001,https://localhost:8001,http://127.0.0.1:8001,https://127.0.0.1:8001",
)

# Forzar inclusión de https://localhost:8000 por si hay override posterior
if "https://localhost:8000" not in CSRF_TRUSTED_ORIGINS:
    CSRF_TRUSTED_ORIGINS.append("https://localhost:8000")
if "https://127.0.0.1:8000" not in CSRF_TRUSTED_ORIGINS:
    CSRF_TRUSTED_ORIGINS.append("https://127.0.0.1:8000")

# Añadir hosts de Codespaces/preview si existen
CODESPACE = env("CODESPACE_NAME") or env("GITHUB_CODESPACE_NAME") or ""
if CODESPACE:
    CSRF_TRUSTED_ORIGINS.extend([
        f"https://{CODESPACE}-8000.app.github.dev",
        f"http://{CODESPACE}-8000.app.github.dev",
        f"https://{CODESPACE}-8000.{env('GITHUB_CODESPACES_PORT_FORWARDING_DOMAIN', 'app.github.dev')}",
        f"http://{CODESPACE}-8000.{env('GITHUB_CODESPACES_PORT_FORWARDING_DOMAIN', 'app.github.dev')}",
    ])

# También soportar cualquier dominio *.app.github.dev que venga por env
_extra = env("CSRF_TRUSTED_ORIGINS_EXTRA", "")
if _extra:
    CSRF_TRUSTED_ORIGINS.extend([x.strip() for x in _extra.split(",") if x.strip()])

# Incluir el dominio de preview exacto detectado
CSRF_TRUSTED_ORIGINS.extend([
    "https://redesigned-space-waddle-6965q9p46qw72xvj-8000.app.github.dev",
    "http://redesigned-space-waddle-6965q9p46qw72xvj-8000.app.github.dev",
])

ALLOWED_HOSTS = list(ALLOWED_HOSTS) if isinstance(ALLOWED_HOSTS, list) else []
ALLOWED_HOSTS.extend(["localhost", "127.0.0.1", "[::1]", "testserver"])
if CODESPACE:
    dom = env("GITHUB_CODESPACES_PORT_FORWARDING_DOMAIN", "app.github.dev")
    ALLOWED_HOSTS.append(f"{CODESPACE}-8000.app.github.dev")
    ALLOWED_HOSTS.append(f"{CODESPACE}-8000.{dom}")
ALLOWED_HOSTS.extend([
    "redesigned-space-waddle-6965q9p46qw72xvj-8000.app.github.dev",
])
ALLOWED_HOSTS = list({h for h in ALLOWED_HOSTS if h})

# Cookies seguras cuando hay HTTPS en producción
SECURE_SSL_REDIRECT = env_bool("DJANGO_SECURE_SSL_REDIRECT", False)
SESSION_COOKIE_SECURE = env_bool("DJANGO_SECURE_COOKIES", not DEBUG)
CSRF_COOKIE_SECURE = env_bool("DJANGO_SECURE_COOKIES", not DEBUG)
SECURE_HSTS_SECONDS = int(env("DJANGO_HSTS_SECONDS", "0"))
SECURE_HSTS_INCLUDE_SUBDOMAINS = env_bool("DJANGO_HSTS_INCLUDE_SUBDOMAINS", False)
SECURE_HSTS_PRELOAD = env_bool("DJANGO_HSTS_PRELOAD", False)

# Detrás de un proxy inverso (Nginx, Caddy, Cloudflare) hay que confiar en
# el header X-Forwarded-Proto para que el HTTPS se detecte correctamente.
if env_bool("DJANGO_TRUST_PROXY", not DEBUG):
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

# --- Aplicaciones -----------------------------------------------------------
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.humanize",
    # Apps del proyecto
    "apps.accounts",
    "apps.catalogo",
    "apps.pedidos",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

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
                "apps.pedidos.context_processors.carrito",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

# --- Base de datos ----------------------------------------------------------
# Si existe DATABASE_URL manda sobre las variables POSTGRES_*
_database_url = env("DATABASE_URL")

if _database_url:
    DATABASES = {
        "default": dj_database_url.parse(
            _database_url, conn_max_age=600, conn_health_checks=True
        )
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": env("POSTGRES_DB", "diaromas"),
            "USER": env("POSTGRES_USER", "diaromas"),
            "PASSWORD": env("POSTGRES_PASSWORD", "diaromas_dev_password"),
            "HOST": env("POSTGRES_HOST", "localhost"),
            "PORT": env("POSTGRES_PORT", "5432"),
            "CONN_MAX_AGE": 600,
            "CONN_HEALTH_CHECKS": True,
        }
    }

# Timeout de conexión: evita que la app se cuelgue si la base de datos no responde
DATABASES["default"].setdefault("OPTIONS", {})
DATABASES["default"]["OPTIONS"].setdefault(
    "connect_timeout", env("POSTGRES_CONNECT_TIMEOUT", "5")
)

# Control de migraciones automáticas (lo ejecuta el entrypoint del contenedor)
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# --- Autenticación ----------------------------------------------------------
AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation."
        "UserAttributeSimilarityValidator"
    },
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LOGIN_URL = "accounts:login"
LOGIN_REDIRECT_URL = "home"
LOGOUT_REDIRECT_URL = "home"

# --- Internacionalización ----------------------------------------------------
LANGUAGE_CODE = "es-cl"
TIME_ZONE = "America/Santiago"
USE_I18N = True
USE_TZ = True

# --- Archivos estáticos y medias -------------------------------------------
STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [BASE_DIR / "static"]

MEDIA_URL = "media/"
MEDIA_ROOT = BASE_DIR / "media"

STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
    "staticfiles": {
        # Con Manifest falla si falta un archivo; en dev usamos la versión simple.
        "BACKEND": (
            "django.contrib.staticfiles.storage.StaticFilesStorage"
            if DEBUG
            else "whitenoise.storage.CompressedManifestStaticFilesStorage"
        )
    },
}

# --- Datos del negocio ------------------------------------------------------
# Número de WhatsApp en formato internacional, solo dígitos (sin '+' ni espacios)
WHATSAPP_NUMBER = env("WHATSAPP_NUMBER", "56987654321")

CURRENCY = env("CURRENCY", "CLP")
IVA_RATE = Decimal(env("IVA_RATE", "0.19"))
IVA_INCLUDED = env_bool("IVA_INCLUDED", True)

NOMBRE_NEGOCIO = env("NOMBRE_NEGOCIO", "Diaromas")
# Nota de entrega que se incluye al final del mensaje de WhatsApp
CONDICION_ENVIO = env("CONDICION_ENVIO", "Envío a coordinar con el negocio")
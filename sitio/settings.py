# sitio/settings.py
import os
import dj_database_url
from pathlib import Path

# ─── Ruta base del proyecto ───────────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent.parent

# ─── Seguridad ────────────────────────────────────────────────────────────────
# SECRET_KEY debe estar en la variable de entorno. El fallback solo sirve para
# desarrollo local; en producción Railway/Render la inyectan automáticamente.
SECRET_KEY = os.getenv("SECRET_KEY", "dev-key-insegura-cambiar-en-produccion")

# DEBUG=True en local, DEBUG=False en producción.
# Railway setea DEBUG=False; en local no setees esta variable y queda True.
DEBUG = os.getenv("DEBUG", "True") == "True"

# En Railway: ALLOWED_HOSTS=tuapp.up.railway.app
# En local: deja la variable vacía o no la definas (usará "*")
_allowed = os.getenv("ALLOWED_HOSTS", "")
ALLOWED_HOSTS = _allowed.split(",") if _allowed else ["*"]

# ─── Aplicaciones ─────────────────────────────────────────────────────────────
INSTALLED_APPS = [
    "django_extensions",
    "django.contrib.sites",
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",

    "app_estacionamiento",

    "allauth",
    "allauth.account",
    "allauth.socialaccount",
    "allauth.socialaccount.providers.google",
]

# SITE_ID debe coincidir con el ID del registro en Django Admin → Sites.
# Se puede sobreescribir con variable de entorno en Railway si el ID cambia.
SITE_ID = int(os.environ.get("SITE_ID", 2))

# ─── Middleware ───────────────────────────────────────────────────────────────
# WhiteNoise va justo después de SecurityMiddleware para servir estáticos en prod.
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",   # ← archivos estáticos en prod
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "allauth.account.middleware.AccountMiddleware",
]

SESSION_ENGINE = "django.contrib.sessions.backends.db"

ROOT_URLCONF = "sitio.urls"
WSGI_APPLICATION = "sitio.wsgi.application"

# ─── Templates ────────────────────────────────────────────────────────────────
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
                # Inyecta municipio_branding (logo, colores, nombre) en todos los templates
                "app_estacionamiento.context_processors.municipio_branding",
            ],
        },
    },
]

# ─── Base de datos ────────────────────────────────────────────────────────────
# En Railway/Render: DATABASE_URL se inyecta automáticamente desde el add-on de PostgreSQL.
# En local sin DATABASE_URL: usa SQLite.
_database_url = os.getenv("DATABASE_URL")
if _database_url:
    DATABASES = {"default": dj_database_url.parse(_database_url, conn_max_age=600)}
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }

# ─── Autenticación ────────────────────────────────────────────────────────────
AUTH_USER_MODEL = "app_estacionamiento.Usuario"

AUTHENTICATION_BACKENDS = [
    "django.contrib.auth.backends.ModelBackend",
    "allauth.account.auth_backends.AuthenticationBackend",
]

# Validadores de contraseña: activos en producción, relajados en desarrollo
# para no tener que usar contraseñas complejas al crear usuarios de prueba.
if DEBUG:
    AUTH_PASSWORD_VALIDATORS = []
else:
    AUTH_PASSWORD_VALIDATORS = [
        {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
        {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
        {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
        {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
    ]

# ─── Seguridad adicional en producción ───────────────────────────────────────
if not DEBUG:
    CSRF_COOKIE_SECURE = True
    SESSION_COOKIE_SECURE = True
    SECURE_BROWSER_XSS_FILTER = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    SECURE_HSTS_SECONDS = 31536000
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    # Railway/Render terminan el SSL en el proxy y pasan este header.
    # Sin esto Django no detecta que la conexión es HTTPS y rompe redirects.
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

# W008 (SECURE_SSL_REDIRECT) se silencia porque Railway maneja el redirect
# a HTTPS en el load balancer. Activarlo en Django causaría redirect loops.
SILENCED_SYSTEM_CHECKS = ["security.W008"]

# ─── CSRF ─────────────────────────────────────────────────────────────────────
# En Railway: CSRF_TRUSTED_ORIGINS=https://tuapp.up.railway.app
_csrf_origins = os.getenv("CSRF_TRUSTED_ORIGINS", "http://127.0.0.1:8000,http://localhost:8000")
CSRF_TRUSTED_ORIGINS = [o.strip() for o in _csrf_origins.split(",")]

# ─── Internacionalización ─────────────────────────────────────────────────────
LANGUAGE_CODE = "es-ar"
USE_I18N = True
USE_TZ = True
TIME_ZONE = "America/Argentina/Buenos_Aires"

# ─── Archivos estáticos ───────────────────────────────────────────────────────
STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [BASE_DIR / "static"]

# WhiteNoise comprime y cachea los estáticos automáticamente en producción.
STATICFILES_STORAGE = "whitenoise.storage.CompressedStaticFilesStorage"

# ─── Archivos de media (fotos infracciones) ───────────────────────────────────
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

# ─── Login / Logout ───────────────────────────────────────────────────────────
LOGIN_URL = "/usuarios/login/"
LOGIN_REDIRECT_URL = "/"

# ─── Allauth (login solo con email, sin username) ─────────────────────────────
ACCOUNT_LOGIN_METHODS = {"email"}
ACCOUNT_SIGNUP_FIELDS = ["email*", "password1*", "password2*"]
ACCOUNT_EMAIL_VERIFICATION = "none"
ACCOUNT_USER_MODEL_USERNAME_FIELD = None
ACCOUNT_USERNAME_REQUIRED = False
ACCOUNT_EMAIL_REQUIRED = True
ACCOUNT_AUTHENTICATION_METHOD = "email"
ACCOUNT_ADAPTER = "app_estacionamiento.adapters.NoUsernameAccountAdapter"
# Adapter social: mapea email de Google al campo 'correo' de nuestro modelo
SOCIALACCOUNT_ADAPTER = "app_estacionamiento.adapters.SocialAccountAdapter"
SOCIALACCOUNT_AUTO_SIGNUP = True
# Campo email del modelo de usuario (usamos 'correo' en lugar del estándar 'email')
ACCOUNT_USER_MODEL_EMAIL_FIELD = "correo"
# Forzar HTTPS en las URLs de callback de OAuth (Railway termina SSL en el proxy)
ACCOUNT_DEFAULT_HTTP_PROTOCOL = "https"

# Configuración de la app de Google directamente en settings,
# sin necesitar un registro SocialApp en la base de datos.
SOCIALACCOUNT_PROVIDERS = {
    "google": {
        "APP": {
            "client_id": os.getenv("GOOGLE_CLIENT_ID", ""),
            "secret": os.getenv("GOOGLE_CLIENT_SECRET", ""),
        },
        "SCOPE": ["profile", "email"],
        "AUTH_PARAMS": {"access_type": "online"},
    }
}

# ─── MercadoPago ──────────────────────────────────────────────────────────────
# En Railway: setear MP_ACCESS_TOKEN con el token de producción o sandbox.
# Obtenerlos en: https://www.mercadopago.com.ar/developers/panel/credentials
MP_ACCESS_TOKEN  = os.getenv("MP_ACCESS_TOKEN", "")
MP_PUBLIC_KEY    = os.getenv("MP_PUBLIC_KEY", "")
MP_CLIENT_ID     = os.getenv("MP_CLIENT_ID", "")
MP_CLIENT_SECRET = os.getenv("MP_CLIENT_SECRET", "")

# ─── Misc ─────────────────────────────────────────────────────────────────────
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Modo de validación de estacionamiento:
# True  = modo producción (valida todo, no permite verificar si hay inconsistencias)
# False = modo desarrollo (permisivo, más rápido para testear)
VALIDACION_ACTIVA = not DEBUG

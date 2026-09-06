# sitio/settings.py
import os
import dj_database_url
from pathlib import Path

# ─── Ruta base del proyecto ───────────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent.parent

# ─── Seguridad ────────────────────────────────────────────────────────────────
# DEBUG se define primero para que SECRET_KEY pueda depender de él.
# Railway setea DEBUG=False; en local no setees esta variable y queda True.
DEBUG = os.getenv("DEBUG", "True") == "True"

# SECRET_KEY: en local usa el fallback inseguro solo si DEBUG=True.
# En producción (DEBUG=False) sin SECRET_KEY falla al arrancar — mejor que
# correr con una clave pública que cualquiera puede usar para forjar sesiones.
_secret_key = os.getenv("SECRET_KEY", "dev-key-insegura-cambiar-en-produccion" if DEBUG else "")
if not _secret_key:
    from django.core.exceptions import ImproperlyConfigured
    raise ImproperlyConfigured(
        "SECRET_KEY no está configurada. Agregar la variable de entorno SECRET_KEY en Railway."
    )
SECRET_KEY = _secret_key

# MP_SANDBOX controla si MercadoPago usa el sandbox o producción.
# Por defecto sigue a DEBUG: True en local, False en producción.
# Para forzar producción en local: MP_SANDBOX=False en .env
# Para forzar sandbox en producción: MP_SANDBOX=True en Railway vars
MP_SANDBOX = os.getenv("MP_SANDBOX", str(DEBUG)) == "True"

# En Railway: ALLOWED_HOSTS=tuapp.up.railway.app
# En local: deja la variable vacía (usará "*" solo si DEBUG=True).
# Si DEBUG=False sin ALLOWED_HOSTS, falla ruidosamente en lugar de quedar abierto.
_allowed = os.getenv("ALLOWED_HOSTS", "")
ALLOWED_HOSTS = _allowed.split(",") if _allowed else (["*"] if os.getenv("DEBUG", "True") == "True" else ["localhost", "127.0.0.1"])

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

    "axes",   # rate limiting: bloqueo por IP después de N intentos fallidos

    # anymail: backend de email transaccional (Resend vía API HTTPS, no SMTP)
    # Debe estar en INSTALLED_APPS para que Django reconozca el backend.
    "anymail",
]

# SITE_ID debe coincidir con el ID del registro en Django Admin → Sites.
# Se puede sobreescribir con variable de entorno en Railway si el ID cambia.
SITE_ID = int(os.environ.get("SITE_ID", 2))

# ─── Middleware ───────────────────────────────────────────────────────────────
# WhiteNoise va justo después de SecurityMiddleware para servir estáticos en prod.
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",        # ← archivos estáticos en prod
    "axes.middleware.AxesMiddleware",                   # ← rate limiting (debe ir antes de SessionMiddleware)
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "allauth.account.middleware.AccountMiddleware",
    # Redirige a completar-perfil si el usuario no tiene municipio asignado
    # (solo en sistemas con más de un municipio activo)
    "app_estacionamiento.middleware.RequiereMunicipioMiddleware",
    # Redirige a /cambiar-password/ si el admin le asignó una contraseña temporal
    # y el usuario todavía no la cambió (impide saltear el formulario navegando directo)
    "app_estacionamiento.middleware.ForzarCambioPasswordMiddleware",
]

SESSION_ENGINE = "django.contrib.sessions.backends.db"
# 12 horas: razonable para tablets de inspectores y kioskos compartidos.
# allauth respeta este valor; las sesiones se renuevan en cada login.
SESSION_COOKIE_AGE = 43200

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
    # axes debe ser el primero: verifica lockout antes de que los demás backends autentiquen
    "axes.backends.AxesStandaloneBackend",
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
    # Evita que el browser filtre la URL actual en el header Referer al salir del sistema.
    # "same-origin" = envía Referer solo a URLs del mismo dominio; nada a externos.
    SECURE_REFERRER_POLICY = "same-origin"
    # Railway/Render terminan el SSL en el proxy y pasan este header.
    # Sin esto Django no detecta que la conexión es HTTPS y rompe redirects.
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

# W008 (SECURE_SSL_REDIRECT) se silencia porque Railway maneja el redirect
# a HTTPS en el load balancer. Activarlo en Django causaría redirect loops.
SILENCED_SYSTEM_CHECKS = ["security.W008"]

# ─── Error tracking — Sentry ─────────────────────────────────────────────────
# Solo activo en producción (DEBUG=False) y si SENTRY_DSN está seteada.
# En Railway: agregar variable SENTRY_DSN con el DSN del proyecto en sentry.io.
# traces_sample_rate=0.1 → captura el 10% de las transacciones para performance
# (suficiente para detectar cuellos de botella sin llenar la cuota del plan free).
_sentry_dsn = os.getenv("SENTRY_DSN", "").strip()
if not DEBUG and _sentry_dsn:
    import sentry_sdk
    sentry_sdk.init(
        dsn=_sentry_dsn,
        traces_sample_rate=0.1,
        send_default_pii=False,   # no envía datos personales (correo, IP) a Sentry
    )

# ─── Rate limiting — django-axes ──────────────────────────────────────────────
# Bloquea después de AXES_FAILURE_LIMIT intentos fallidos consecutivos.
# El bloqueo dura AXES_COOLOFF_TIME horas y se resetea al entrar exitosamente.
#
# AXES_LOCKOUT_PARAMETERS con lista anidada [["ip_address", "username"]]:
#   bloquea cuando la MISMA IP intenta entrar con el MISMO correo 5 veces.
#   → Un atacante que cambia de IP no acumula intentos (protege al usuario legítimo).
#   → Un atacante que prueba distintos correos desde la misma IP no acumula (no bloquea IPs compartidas).
#   → Solo bloquea cuando el ataque es dirigido: misma IP + mismo correo.
#
# AXES_USERNAME_FORM_FIELD: nuestro form usa "correo" en lugar del estándar "username".
# Sin esto, axes no puede rastrear intentos por correo y el umbral combinado no funciona.
AXES_FAILURE_LIMIT      = 5                              # intentos fallidos antes de bloquear
AXES_COOLOFF_TIME       = 1                              # horas bloqueado (acepta int o timedelta)
AXES_RESET_ON_SUCCESS   = True                           # resetea el contador al loguearse bien
AXES_USERNAME_FORM_FIELD = "correo"                      # campo de email en nuestro form de login
AXES_LOCKOUT_PARAMETERS = [["ip_address", "username"]]  # bloquea por IP + correo combinados
AXES_LOCKOUT_TEMPLATE   = "lockout.html"                 # template para la pantalla de bloqueo

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

# Django 5.x: STORAGES reemplaza DEFAULT_FILE_STORAGE y STATICFILES_STORAGE.
# Se define acá con WhiteNoise para estáticos; el bloque de Cloudinary
# agrega el "default" si las variables están seteadas.
STORAGES = {
    # "default" siempre presente (Django 5.x lo requiere aunque no haya media files).
    # Si Cloudinary está configurado, el bloque de abajo sobreescribe este valor.
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedStaticFilesStorage",
    },
}

# ─── Archivos de media (fotos infracciones, logos) ───────────────────────────
# Si las variables de Cloudinary están seteadas (en Railway), las fotos se
# suben automáticamente a la nube. En local sin esas variables, usa el filesystem.
_cloudinary_cloud = os.getenv("CLOUDINARY_CLOUD_NAME", "").strip()
if _cloudinary_cloud:
    INSTALLED_APPS += ["cloudinary_storage", "cloudinary"]

    CLOUDINARY_STORAGE = {
        "CLOUD_NAME": _cloudinary_cloud,
        "API_KEY":    os.getenv("CLOUDINARY_API_KEY", ""),
        "API_SECRET": os.getenv("CLOUDINARY_API_SECRET", ""),
    }
    # "default" = storage para ImageField/FileField → Cloudinary
    STORAGES["default"] = {
        "BACKEND": "cloudinary_storage.storage.MediaCloudinaryStorage",
    }
    # MEDIA_URL vacío: django-cloudinary-storage construye la URL completa de Cloudinary
    # internamente. Si se setea a la URL base de Cloudinary, la URL se duplica.
    MEDIA_URL = ""
    MEDIA_ROOT = ""  # No se usa con Cloudinary
else:
    # Desarrollo local: filesystem normal
    MEDIA_URL = "/media/"
    MEDIA_ROOT = BASE_DIR / "media"

# ─── Email ────────────────────────────────────────────────────────────────────
# Prioridad:
#   1. RESEND_API_KEY → usa Resend vía API HTTPS (recomendado en Railway, no depende de SMTP)
#   2. EMAIL_HOST_USER → usa SMTP directo (solo funciona si el proveedor no bloquea puerto 587)
#   3. Sin variables → consola (desarrollo local)
#
# Para Railway: configurar RESEND_API_KEY + DEFAULT_FROM_EMAIL en Variables.
# Obtener API key en https://resend.com (free: 100 emails/día).
# FROM address para pruebas: onboarding@resend.dev (no requiere dominio verificado).
# Para producción: verificar tu dominio en Resend y usar noreply@tudominio.com.
if os.getenv("BREVO_API_KEY"):
    # Brevo (ex-Sendinblue): API HTTPS, sin dominio propio, solo verificar email remitente.
    # Crear cuenta en brevo.com → Settings → API Keys.
    EMAIL_BACKEND = "anymail.backends.brevo.EmailBackend"
    ANYMAIL = {
        "BREVO_API_KEY": os.getenv("BREVO_API_KEY"),
    }
elif os.getenv("RESEND_API_KEY"):
    # Resend: requiere dominio verificado en resend.com/domains para enviar a cualquier destinatario.
    EMAIL_BACKEND  = "anymail.backends.resend.EmailBackend"
    ANYMAIL = {
        "RESEND_API_KEY": os.getenv("RESEND_API_KEY"),
    }
elif os.getenv("EMAIL_HOST_USER"):
    EMAIL_BACKEND   = "django.core.mail.backends.smtp.EmailBackend"
    EMAIL_HOST      = os.getenv("EMAIL_HOST", "smtp.gmail.com")
    EMAIL_PORT      = int(os.getenv("EMAIL_PORT", "587"))
    EMAIL_USE_TLS   = True
    EMAIL_HOST_USER     = os.getenv("EMAIL_HOST_USER", "")
    EMAIL_HOST_PASSWORD = os.getenv("EMAIL_HOST_PASSWORD", "")
else:
    EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

DEFAULT_FROM_EMAIL = os.getenv("DEFAULT_FROM_EMAIL", "Sistema de Estacionamiento <noreply@estacionamiento.ar>")

# ─── Login / Logout ───────────────────────────────────────────────────────────
LOGIN_URL = "/login/"
LOGIN_REDIRECT_URL = "/"

# ─── Allauth (login solo con email, sin username) ─────────────────────────────
ACCOUNT_LOGIN_METHODS = {"email"}
ACCOUNT_SIGNUP_FIELDS = ["email*", "password1*", "password2*"]
ACCOUNT_EMAIL_VERIFICATION = os.getenv("ACCOUNT_EMAIL_VERIFICATION", "none")
# Después de confirmar el email, intentar auto-loguear al usuario.
# Funciona en conjunto con ACCOUNT_EMAIL_VERIFICATION = "mandatory".
ACCOUNT_LOGIN_ON_EMAIL_CONFIRMATION = True
ACCOUNT_USER_MODEL_USERNAME_FIELD = None
ACCOUNT_ADAPTER = "app_estacionamiento.adapters.NoUsernameAccountAdapter"
# Adapter social: mapea email de Google al campo 'correo' de nuestro modelo
SOCIALACCOUNT_ADAPTER = "app_estacionamiento.adapters.SocialAccountAdapter"
SOCIALACCOUNT_AUTO_SIGNUP = True
# Siempre recordar la sesión (cookie persistente, no de solo sesión de browser)
ACCOUNT_SESSION_REMEMBER = True
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
MP_ACCESS_TOKEN   = os.getenv("MP_ACCESS_TOKEN", "")
MP_PUBLIC_KEY     = os.getenv("MP_PUBLIC_KEY", "")
MP_CLIENT_ID      = os.getenv("MP_CLIENT_ID", "")
MP_CLIENT_SECRET  = os.getenv("MP_CLIENT_SECRET", "")
# Secreto del webhook MP para verificar la firma HMAC-SHA256 del header x-signature.
# Obtenerlo en: MP Dashboard → Tus integraciones → [tu app] → Webhooks → secreto.
# En Railway: setear como variable MP_WEBHOOK_SECRET.
# Sin esta variable, la verificación se omite (modo permisivo para entornos de prueba).
MP_WEBHOOK_SECRET = os.getenv("MP_WEBHOOK_SECRET", "")

# ─── Misc ─────────────────────────────────────────────────────────────────────
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Modo de validación de estacionamiento:
# True  = modo producción (valida todo, no permite verificar si hay inconsistencias)
# False = modo desarrollo (permisivo, más rápido para testear)
VALIDACION_ACTIVA = not DEBUG
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {"console": {"class": "logging.StreamHandler"}},
    "loggers": {
        "django.request": {"handlers": ["console"], "level": "DEBUG", "propagate": False},
    },
}
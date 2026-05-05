#sitio/settings.py
import os
from pathlib import Path

# 🏠 Ruta base del proyecto
BASE_DIR = Path(__file__).resolve().parent.parent

# 🔐 Seguridad básica
DEBUG = True
ALLOWED_HOSTS = ["*"] # En producción, ALLOWED_HOSTS = ["tudominio.com"]

STATICFILES_DIRS = [
    BASE_DIR / "static",
]

# 🧩 Aplicaciones instaladas
INSTALLED_APPS = [
    "django_extensions",
    'django.contrib.sites',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    'app_estacionamiento',

    #'allauth',
    #'allauth.account',
    #'allauth.socialaccount',
    # 'allauth.socialaccount.providers.google', # Login con Google
]

# ⚙️ Middleware (control de peticiones)

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

SESSION_ENGINE = 'django.contrib.sessions.backends.db'

ROOT_URLCONF = 'sitio.urls'

# 🌐 Configuración de sitios (para allauth)
SITE_ID = 1

AUTHENTICATION_BACKENDS = [
    "django.contrib.auth.backends.ModelBackend",
]

ENV = os.getenv("ENV", "dev")

if ENV == "prod":
    CSRF_COOKIE_SECURE = True
    SESSION_COOKIE_SECURE = True
    SECURE_BROWSER_XSS_FILTER = True
    SECURE_CONTENT_TYPE_NOSNIFF = True

# 🎨 Templates (HTML)
TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],  # 👈 carpeta templates en la raíz del proyecto
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

WSGI_APPLICATION = 'sitio.wsgi.application'

# 🧠 Base de datos SQLite (local)
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

AUTH_USER_MODEL = "app_estacionamiento.Usuario"


# 🔑 Validadores de contraseña
AUTH_PASSWORD_VALIDATORS = []

# 🌎 Config regional
LANGUAGE_CODE = 'es-ar'
USE_I18N = True
USE_TZ = True
TIME_ZONE = 'America/Argentina/Buenos_Aires'

# 🖼️ Archivos estáticos
STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

# 🖼️ Fotos infracciones
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')


# Para producción (cuando uses collectstatic)
STATIC_ROOT = BASE_DIR / "staticfiles"
VALIDACION_ACTIVA = False # True El sistema FUNCIONA (permite verificar) valida (modo estricto / producción) True = versión segura (la que vas a vender - False El sistema NO FUNCIONA (no permite verificar) - Modo desarrollo NO valida (modo barato / MVP)  False = versión rápida, flexible

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
SECRET_KEY = os.getenv("SECRET_KEY", "dev-key")

# redirireccion correcta.

LOGIN_URL = "login"
LOGIN_REDIRECT_URL = "inicio"
LOGOUT_REDIRECT_URL = "login"


CSRF_TRUSTED_ORIGINS = [
    "http://127.0.0.1:8000",
]



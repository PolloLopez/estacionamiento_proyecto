# app_estacionamiento/sitio/urls.py

from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from app_estacionamiento.views import inicio

urlpatterns = [
    # 🌐 ROOT → redirección inteligente por rol
    path("", inicio, name="inicio"),

    # 🔐 ADMIN DJANGO — URL no obvia para reducir bruteforce de bots
    path("sistema-interno/", admin.site.urls),

    # 🔐 AUTH EXTERNO
    path("accounts/", include("allauth.urls")),

    # 🔌 APP PRINCIPAL — sin prefijo, URLs directas en raíz
    path("", include("app_estacionamiento.urls")),
]

# Servir media localmente SOLO si Cloudinary no está configurado (desarrollo local).
# Con Cloudinary activo, las URLs de media apuntan directo a la CDN de Cloudinary.
if settings.MEDIA_ROOT:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
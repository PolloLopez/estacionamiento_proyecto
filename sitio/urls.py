# app_estacionamiento/sitio/urls.py

from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from app_estacionamiento.views import inicio

urlpatterns = [
    # 🌐 ROOT → redirección inteligente por rol
    path("", inicio, name="inicio"),

    # 🔐 ADMIN DJANGO
    path("admin/", admin.site.urls),

    # 🔌 APP PRINCIPAL
    path("usuarios/", include("app_estacionamiento.urls")),

    # 🔐 AUTH EXTERNO
    path("accounts/", include("allauth.urls")),
]

# Servir archivos de media a través de Django.
# En producción (Railway) no hay servidor web externo que sirva /media/,
# así que Django lo hace directamente. No ideal para alta carga, pero
# suficiente para el volumen actual. Reemplazar con Cloudinary cuando esté listo.
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
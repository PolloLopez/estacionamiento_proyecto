# app_estacionamiento/sitio/urls.py

from django.contrib import admin
from django.urls import path, include
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
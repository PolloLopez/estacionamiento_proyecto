# sitio/urls.py

from django.contrib import admin
from django.urls import path, include
from django.shortcuts import redirect

urlpatterns = [
    path("admin/", admin.site.urls),

    # root → manda a inicio inteligente
    path("", lambda request: redirect("inicio")),

    # app completa
    path("usuarios/", include("app_estacionamiento.urls")),

    path("accounts/", include("allauth.urls")),
]
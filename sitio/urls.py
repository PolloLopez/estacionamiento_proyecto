# app_estacionamiento/sitio/urls.py

from django import views
from django.contrib import admin
from django.urls import path, include
from django.shortcuts import redirect

urlpatterns = [
    path("admin/", admin.site.urls),

    path("", lambda request: redirect("inicio")),

    path("usuarios/", include("app_estacionamiento.urls")),
    path("accounts/", include("allauth.urls")),
]
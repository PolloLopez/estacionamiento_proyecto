# app_estacionamiento/sitio/urls.py

from django.contrib import admin
from django.urls import path, include
from django.shortcuts import redirect
from app_estacionamiento.views import inicio
from app_estacionamiento import views

urlpatterns = [
    path("", inicio, name="inicio"),  # 👈 USAR VIEW REAL

    path("admin/", admin.site.urls),
    path("usuarios/login/", views.login_view, name="login"),
    path("", views.inicio, name="inicio"),  # Redirige la raíz a la vista de inicio 

    path("usuarios/", include("app_estacionamiento.urls")),
    path("accounts/", include("allauth.urls")),
    path(
    "inspectores/ticket/<int:infraccion_id>/",
    views.ticket_infraccion,
    name="inspectores_ticket"
    ),
    path(
    "inspectores/ticket-cobro/<int:est_id>/",
    views.ticket_cobro,
    name="inspectores_ticket_cobro"
    ),
    path("vehiculo/agregar/", views.agregar_vehiculo, name="agregar_vehiculo"),
]

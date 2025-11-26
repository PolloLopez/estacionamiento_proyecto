# sitio/urls.py
from django.contrib import admin
from django.urls import path
from app_estacionamiento import views

urlpatterns = [
    path("", views.inicio, name="inicio"),
    path("login/", views.login_view, name="login"),
    path("logout/", views.logout_view, name="logout"), 

    # Usuarios
    path("usuarios/estacionar/", views.estacionar_vehiculo, name="usuarios_estacionar_vehiculo"),
    path("usuarios/finalizar/<int:estacionamiento_id>/", views.finalizar_estacionamiento, name="usuarios_finalizar_estacionamiento"),

    # Inspectores
    path("inspectores/verificar/", views.verificar_vehiculo, name="inspectores_verificar_vehiculo"),
    path("inspectores/infraccion/", views.registrar_infraccion, name="inspectores_registrar_infraccion"),

    # Vendedores
    path("vendedores/panel/", views.panel_vendedores, name="panel_vendedores"),
    path("vendedores/registrar/", views.registrar_estacionamiento_vendedor, name="vendedores_registrar_estacionamiento"),
    path("vendedores/resumen/", views.resumen_caja, name="vendedores_resumen_caja"),

    # Admin
    path("admin/", views.panel_admin, name="panel_admin"),
    path("admin/cargar_saldo/<int:usuario_id>/", views.cargar_saldo, name="cargar_saldo"),
]

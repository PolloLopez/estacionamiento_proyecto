# sitio/urls.py
from django.urls import path
from app_estacionamiento import views

urlpatterns = [
    # Usuarios
    path("usuarios/estacionar/", views.estacionar_vehiculo, name="usuarios_estacionar_vehiculo"),
    path("usuarios/finalizar/<int:estacionamiento_id>/", views.finalizar_estacionamiento, name="usuarios_finalizar_estacionamiento"),

    # Inspectores
    path("inspectores/verificar/", views.verificar_vehiculo, name="inspectores_verificar_vehiculo"),
    path("inspectores/infraccion/", views.registrar_infraccion, name="inspectores_registrar_infraccion"),

    # Vendedores
    path("vendedores/estacionar/", views.registrar_estacionamiento_vendedor, name="vendedores_estacionar"),
    path("vendedores/resumen/", views.resumen_caja, name="vendedores_resumen_caja"),

    # Admin
    path("admin/", views.panel_admin, name="panel_admin"),
]

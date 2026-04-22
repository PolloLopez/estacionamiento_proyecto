# app_estacionamiento/urls.py
from django.urls import path
from . import views

urlpatterns = [
    # auth
    path("login/", views.login_view, name="login"),
    path("logout/", views.logout_view, name="logout"),
    path("registro/", views.registro_view, name="registro"),

    # inicio inteligente
    path("inicio/", views.inicio, name="inicio"),

    # conductor
    path("estacionar/", views.estacionar_vehiculo, name="estacionar"),
    path("finalizar/<int:estacionamiento_id>/", views.finalizar_estacionamiento, name="finalizar"),
    path("historial/", views.historial_estacionamientos, name="historial"),

    # usuario
    path("infracciones/", views.usuarios_infracciones, name="usuarios_infracciones"),
    path("deuda/", views.consultar_deuda, name="consultar_deuda"),

    # inspector
    path("inspectores/", views.panel_inspectores, name="panel_inspectores"),
    path("inspectores/verificar/", views.verificar_vehiculo, name="inspectores_verificar_vehiculo"),
    path("inspectores/infraccion/", views.registrar_infraccion, name="inspectores_registrar_infraccion"),
    path("inspectores/manual/", views.registrar_estacionamiento_manual, name="inspectores_registrar_estacionamiento_manual"),
    path("inspectores/cobros/", views.resumen_cobros, name="inspectores_resumen_cobros"),
    path("inspectores/resumen/", views.resumen_infracciones, name="inspectores_resumen_infracciones"),

    # vendedor
    path("vendedores/", views.panel_vendedores, name="panel_vendedores"),

    # admin
    path("admin-panel/", views.panel_admin, name="panel_admin"),
    path("admin-exenciones/", views.panel_exenciones, name="exenciones"),
]
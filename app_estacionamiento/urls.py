# app_estacionamiento/urls.py

from django.urls import path
from . import views

urlpatterns = [

    # =========================
    # 🔐 AUTH
    # =========================
    path("login/", views.login_view, name="login"),
    path("logout/", views.logout_view, name="logout"),
    path("registro/", views.registro_view, name="registro"),

    # =========================
    # 🧭 INICIO
    # =========================
    path("inicio/", views.inicio_usuarios, name="inicio"),

    # =========================
    # 🚗 CONDUCTORES
    # =========================
    path("estacionar/", views.estacionar_vehiculo, name="usuarios_estacionar_vehiculo"),

    path("finalizar/<int:estacionamiento_id>/", views.finalizar_estacionamiento, name="usuarios_finalizar_estacionamiento"),

    path("historial/", views.historial_estacionamientos, name="usuarios_historial_estacionamientos"),

    path("mis-estacionamientos/", views.mis_estacionamientos, name="usuarios_mis_estacionamientos"),

    path("infracciones/", views.usuarios_infracciones, name="usuarios_historial_infracciones"),

    path("deuda/", views.consultar_deuda, name="consultar_deuda"),

    # =========================
    # 👮 INSPECTORES
    # =========================
    path("inspectores/", views.panel_inspectores, name="panel_inspectores"),

    path("inspectores/verificar/", views.verificar_vehiculo, name="inspectores_verificar_vehiculo"),

    path("inspectores/verificar_calle/", views.verificar_vehiculo_calle, name="inspectores_verificar_vehiculo_calle"),

    path("inspectores/infraccion/", views.registrar_infraccion, name="inspectores_registrar_infraccion"),

    path("inspectores/manual/", views.registrar_estacionamiento_manual, name="inspectores_registrar_estacionamiento_manual"),

    path("inspectores/cobros/", views.resumen_cobros, name="inspectores_resumen_cobros"),

    path("inspectores/resumen/", views.resumen_infracciones, name="inspectores_resumen_infracciones"),

    path("inspectores/cerrar-caja/", views.cerrar_caja, name="inspectores_cerrar_caja"),

    # =========================
    # 💰 VENDEDORES
    # =========================
    path("vendedores/", views.panel_vendedores, name="panel_vendedores"),

    path("vendedores/registrar/", views.registrar_estacionamiento_vendedor, name="vendedores_registrar_estacionamiento"),

    path("vendedores/resumen/", views.resumen_caja, name="vendedores_resumen_caja"),

    # =========================
    # 💳 SALDO
    # =========================
    path("cargar-saldo/<int:usuario_id>/", views.cargar_saldo, name="cargar_saldo"),

    # =========================
    # 🛠 ADMIN
    # =========================
    path("admin-panel/", views.panel_admin, name="panel_admin"),

    path("admin-exenciones/", views.panel_exenciones, name="exenciones"),
]
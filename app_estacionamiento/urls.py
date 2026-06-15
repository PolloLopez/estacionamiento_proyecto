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
    path("completar-perfil/", views.completar_perfil, name="completar_perfil"),
    path("verificacion/solicitar/", views.solicitar_verificacion, name="solicitar_verificacion"),

    # =========================
    # 🧭 INICIO
    # =========================
    path("inicio/", views.inicio_usuarios, name="inicio_usuarios"),

    # =========================
    # 🚗 CONDUCTORES
    # =========================
    path("estacionar/", views.estacionar_vehiculo, name="usuarios_estacionar_vehiculo"),
    path("finalizar/<int:estacionamiento_id>/", views.finalizar_estacionamiento, name="usuarios_finalizar_estacionamiento"),
    path("gestion-infracciones/", views.gestion_infracciones, name="gestion_infracciones"),
    path("mis-infracciones/", views.mis_infracciones, name="mis_infracciones"),
    path("deuda/", views.consultar_deuda, name="consultar_deuda"),
    path("vehiculo/agregar/", views.agregar_vehiculo, name="agregar_vehiculo"),
    path("vehiculo/<int:vehiculo_id>/eliminar/", views.eliminar_vehiculo, name="eliminar_vehiculo"),
    path("mis_estacionamientos/", views.historial_estacionamientos, name="usuarios_historial_estacionamientos"),
    path("infracciones/<int:infraccion_id>/pagar/",views.pagar_infraccion,name="pagar_infraccion"),

    # =========================
    # 👮 INSPECTORES
    # =========================
    path("inspectores/", views.panel_inspectores, name="panel_inspectores"),
    path("inspectores/verificar/", views.verificar_vehiculo, name="inspectores_verificar_vehiculo"),
    path("inspectores/infraccion/", views.registrar_infraccion, name="inspectores_registrar_infraccion"),
    path("inspectores/manual/", views.registrar_estacionamiento_manual, name="inspectores_registrar_estacionamiento_manual"),
    path("inspectores/cobros/", views.resumen_cobros, name="inspectores_resumen_cobros"),
    path("inspectores/resumen/", views.resumen_infracciones, name="inspectores_resumen_infracciones"),
    path("inspectores/caja/", views.caja_inspector, name="inspectores_caja"),
    path("inspectores/cerrar-caja/", views.cerrar_caja, name="inspectores_cerrar_caja"),
    path("inspectores/ticket/<int:infraccion_id>/", views.ticket_infraccion, name="inspectores_ticket"),
    path("inspectores/ticket-cobro/<int:est_id>/", views.ticket_cobro, name="inspectores_ticket_cobro"),

    # =========================
    # 💰 VENDEDORES
    # =========================
    path("vendedores/", views.panel_vendedor, name="panel_vendedor"),
    path("vendedores/registrar/", views.registrar_estacionamiento_vendedor, name="vendedores_registrar_estacionamiento"),
    path("vendedores/resumen/", views.resumen_caja, name="vendedores_resumen_caja"),
    path("vendedores/caja/", views.caja_inspector, name="vendedores_caja"),
    path("vendedores/cerrar-caja/", views.cerrar_caja, name="vendedores_cerrar_caja"),

    # =========================
    # 💳 SALDO
    # =========================
    path("cargar-saldo/<int:usuario_id>/", views.cargar_saldo, name="cargar_saldo"),

    # =========================
    # 💳 MERCADOPAGO
    # =========================
    path("mp/cargar/", views.mp_iniciar_carga, name="mp_iniciar_carga"),
    path("mp/exitoso/", views.mp_exitoso, name="mp_exitoso"),
    path("mp/fallido/", views.mp_fallido, name="mp_fallido"),
    path("mp/pendiente/", views.mp_pendiente, name="mp_pendiente"),
    path("mp/webhook/", views.mp_webhook, name="mp_webhook"),

    # =========================
    # 🛠 ADMIN
    # =========================
    path("admin-panel/", views.panel_admin, name="panel_admin"),

    # =========================
    # 🛠 GESTIÓN ADMIN
    # =========================
    path("admin-inicio/", views.inicio_admin, name="inicio_admin"),
    path("admin-inspectores/", views.gestionar_inspectores, name="gestionar_inspectores"),
    path("admin-inspectores/<int:inspector_id>/editar/", views.editar_inspector, name="admin_editar_inspector"),
    path("admin-inspectores/crear/", views.gestionar_inspectores, name="admin_crear_inspector"),
    path("admin-vendedores/", views.gestionar_vendedores, name="gestionar_vendedores"),
    path("admin-vendedores/<int:vendedor_id>/editar/", views.editar_vendedor, name="admin_editar_vendedor"),
    path("admin-vendedores/crear/", views.gestionar_vendedores, name="admin_crear_vendedor"),
    path("admin-exenciones/", views.panel_exenciones, name="exenciones"),
    path("admin-usuarios/", views.gestionar_usuarios, name="gestionar_usuarios"),
    path("admin-usuarios/<int:usuario_id>/", views.detalle_usuario_admin, name="detalle_usuario_admin"),
    path("admin-infracciones/", views.admin_infracciones, name="admin_infracciones"),
    path("admin-tarifas/", views.gestionar_tarifas, name="gestionar_tarifas"),
    path("admin-horarios/", views.gestionar_horarios, name="gestionar_horarios"),
    path("admin-dias-especiales/", views.gestionar_dias_especiales, name="gestionar_dias_especiales"),
    path("admin-tarifas/guardar/", views.gestionar_tarifas, name="admin_guardar_tarifa"),

    # =========================
    # 💼 RENDICIONES (ADMIN)
    # =========================
    path("admin-rendiciones/", views.admin_rendiciones, name="admin_rendiciones"),
    path("admin-rendiciones/<int:cierre_id>/certificar/", views.certificar_cierre, name="certificar_cierre"),

    # =========================
    # ✅ VERIFICACIONES
    # =========================
    path("admin-verificaciones/", views.gestionar_verificaciones, name="gestionar_verificaciones"),
    path("admin-verificaciones/<int:solicitud_id>/resolver/", views.resolver_verificacion, name="resolver_verificacion"),

]
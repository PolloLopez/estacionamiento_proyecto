# app_estacionamiento/urls.py

from django.urls import path
from . import views
from . import views_superadmin
from . import views_pwa
from . import views_pago_publico

urlpatterns = [

    # =========================
    # 📱 PWA
    # =========================
    path("manifest.json", views_pwa.manifest_json,  name="manifest_json"),
    path("sw.js",         views_pwa.service_worker, name="service_worker"),

    # =========================
    # 💳 PAGO PÚBLICO (sin registro)
    # =========================
    path("pagar/",                                   views_pago_publico.buscar_patente,            name="pago_publico_buscar"),
    path("pagar/<str:patente>/",                     views_pago_publico.detalle_patente,           name="pago_publico_detalle"),
    path("pagar/infraccion/<int:infraccion_id>/",    views_pago_publico.iniciar_pago_infraccion,   name="pago_publico_infraccion"),
    path("pagar/estacionar/",                        views_pago_publico.iniciar_pago_estacionamiento, name="pago_publico_estacionar"),
    path("pagar/abono/",                             views_pago_publico.iniciar_pago_abono,        name="pago_publico_abono"),
    path("pagar/mp/exitoso/",                        views_pago_publico.mp_exitoso_publico,        name="pago_publico_mp_exitoso"),
    path("pagar/mp/fallido/",                        views_pago_publico.mp_fallido_publico,        name="pago_publico_mp_fallido"),
    path("pagar/mp/pendiente/",                      views_pago_publico.mp_pendiente_publico,      name="pago_publico_mp_pendiente"),
    path("pagar/subcuadra-cercana/",                 views_pago_publico.subcuadra_cercana_publica, name="pago_publico_subcuadra_cercana"),

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
    path("abono/", views.pagar_abono_conductor, name="conductor_pagar_abono"),
    path("deuda/", views.consultar_deuda, name="consultar_deuda"),
    path("vehiculo/agregar/", views.agregar_vehiculo, name="agregar_vehiculo"),
    path("vehiculo/<int:vehiculo_id>/eliminar/", views.eliminar_vehiculo, name="eliminar_vehiculo"),
    path("mis_estacionamientos/", views.historial_estacionamientos, name="usuarios_historial_estacionamientos"),
    path("infracciones/<int:infraccion_id>/pagar/",views.pagar_infraccion,name="pagar_infraccion"),
    path("estacionamiento/<int:est_id>/renovar/", views.renovar_estacionamiento, name="usuarios_renovar_estacionamiento"),
    path("notificacion/<int:notif_id>/leida/", views.marcar_notificacion_leida, name="marcar_notificacion_leida"),

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
    path("inspectores/pdf-infracciones/", views.pdf_infracciones_hoy, name="inspectores_pdf_infracciones"),
    path("inspectores/subcuadra-cercana/", views.subcuadra_cercana, name="inspectores_subcuadra_cercana"),
    path("inspectores/ticket/<int:infraccion_id>/", views.ticket_infraccion, name="inspectores_ticket"),
    path("inspectores/ticket-cobro/<int:est_id>/", views.ticket_cobro, name="inspectores_ticket_cobro"),
    path("ticket-pago-multa/<int:infraccion_id>/", views.ticket_pago_multa, name="ticket_pago_multa"),

    # =========================
    # 💰 VENDEDORES
    # =========================
    path("vendedores/", views.panel_vendedor, name="panel_vendedor"),
    path("vendedores/registrar/", views.registrar_estacionamiento_vendedor, name="vendedores_registrar_estacionamiento"),
    path("vendedores/resumen/", views.resumen_caja, name="vendedores_resumen_caja"),
    path("vendedores/caja/", views.caja_inspector, name="vendedores_caja"),
    path("vendedores/cerrar-caja/", views.cerrar_caja, name="vendedores_cerrar_caja"),
    path("vendedores/cobrar-infraccion/", views.cobrar_infraccion_vendedor, name="vendedores_cobrar_infraccion"),

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
    path("admin-vendedores/<int:vendedor_id>/historial/", views.historial_vendedor, name="admin_historial_vendedor"),
    path("admin-vendedores/crear/", views.gestionar_vendedores, name="admin_crear_vendedor"),
    path("admin-exenciones/", views.panel_exenciones, name="exenciones"),
    path("admin-subcuadras/", views.gestionar_subcuadras, name="gestionar_subcuadras"),
    path("admin-exenciones/importar/", views.importar_exenciones, name="importar_exenciones"),
    path("admin-usuarios/", views.gestionar_usuarios, name="gestionar_usuarios"),
    path("admin-crear-conductor/", views.crear_conductor, name="crear_conductor"),
    path("admin-usuarios/<int:usuario_id>/", views.detalle_usuario_admin, name="detalle_usuario_admin"),
    path("admin-infracciones/", views.admin_infracciones, name="admin_infracciones"),
    path("admin-infracciones/<int:infraccion_id>/comprobante/", views.comprobante_infraccion, name="comprobante_infraccion"),
    path("admin-tarifas/", views.gestionar_tarifas, name="gestionar_tarifas"),
    path("admin-horarios/", views.gestionar_horarios, name="gestionar_horarios"),
    path("admin-dias-especiales/", views.gestionar_dias_especiales, name="gestionar_dias_especiales"),
    path("admin-tarifas/guardar/", views.gestionar_tarifas, name="admin_guardar_tarifa"),

    # =========================
    # 💼 RENDICIONES (ADMIN)
    # =========================
    path("admin-rendiciones/", views.admin_rendiciones, name="admin_rendiciones"),
    path("admin-rendiciones/crear/", views.crear_rendicion, name="crear_rendicion"),
    path("admin-rendiciones/<int:cierre_id>/certificar/", views.certificar_cierre, name="certificar_cierre"),
    path("admin-rendiciones/<int:rendicion_id>/pdf/", views.pdf_rendicion, name="pdf_rendicion"),

    # =========================
    # ✅ VERIFICACIONES
    # =========================
    path("admin-verificaciones/", views.gestionar_verificaciones, name="gestionar_verificaciones"),
    path("admin-verificaciones/<int:solicitud_id>/resolver/", views.resolver_verificacion, name="resolver_verificacion"),
    path("admin-vehiculos/", views.admin_vehiculos, name="admin_vehiculos"),
    path("admin-estacionamientos/", views.admin_estacionamientos, name="admin_estacionamientos"),
    path("admin-inspectores/estadisticas/", views.estadisticas_inspectores, name="estadisticas_inspectores"),
    path("admin-inspectores/estadisticas/excel/", views.estadisticas_inspectores_excel, name="estadisticas_inspectores_excel"),
    path("admin-infracciones/pdf-juzgado/", views.pdf_infracciones_juzgado, name="pdf_infracciones_juzgado"),

    # =========================
    # 📅 ABONO MENSUAL
    # =========================
    path("vendedores/abono/", views.cobrar_abono, name="cobrar_abono"),

    # =========================
    # 💵 COMISIONES VENDEDORES
    # =========================
    path("vendedores/comisiones/", views.mis_comisiones, name="mis_comisiones"),
    path("vendedores/comisiones/<int:liquidacion_id>/certificar/", views.certificar_comision, name="certificar_comision"),
    path("vendedores/comisiones/<int:liquidacion_id>/factura/", views.presentar_factura, name="presentar_factura"),

    # =========================
    # 🏦 TESORERÍA
    # =========================
    path("tesorero/", views.panel_tesorero, name="panel_tesorero"),
    path("tesorero/rendicion/<int:rendicion_id>/validar/", views.validar_rendicion, name="validar_rendicion"),
    path("tesorero/depositar/<int:liquidacion_id>/", views.depositar_comision, name="depositar_comision"),

    # =========================
    # 🌐 SUPERADMIN
    # =========================
    path("superadmin/",                                         views_superadmin.panel_superadmin,  name="panel_superadmin"),
    path("superadmin/municipio/nuevo/",                         views_superadmin.crear_municipio,   name="crear_municipio"),
    path("superadmin/municipio/<int:municipio_id>/",            views_superadmin.editar_municipio,  name="editar_municipio"),
    path("superadmin/municipio/<int:municipio_id>/admin/nuevo/", views_superadmin.crear_admin,      name="crear_admin"),
    path("superadmin/admin/<int:admin_id>/toggle/",             views_superadmin.toggle_admin,      name="toggle_admin"),
    path("superadmin/municipio/<int:municipio_id>/modulo/",     views_superadmin.gestionar_modulo,      name="gestionar_modulo"),
    path("superadmin/municipio/<int:municipio_id>/importar/",   views_superadmin.importar_estacionamientos, name="importar_estacionamientos"),
    path("superadmin/municipio/<int:municipio_id>/plantillas/", views_superadmin.gestionar_plantillas,      name="gestionar_plantillas"),

]

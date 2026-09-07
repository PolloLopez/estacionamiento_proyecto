# ESTACIONAMIENTO_APP/app_estacionamiento/views.py
#
# FACHADA — este archivo importa desde los módulos por rol.
# No definir vistas aquí; agregarlas en el módulo correspondiente.
#
# Módulos activos:
#   views_auth.py       → login, logout, registro, completar_perfil
#   views_inspector.py  → panel, verificar, infracciones, PDF
#   views_tesorero.py   → panel tesorero, depositar comisión
#   views_vendedor.py   → cobros, caja, comisiones
#   views_conductor.py  → estacionar, historial, infracciones propias, vehículos
#   views_admin.py      → panel admin, inspectores, vendedores, tarifas, exenciones, etc.
#   views_mp.py         → integración MercadoPago (carga de saldo)

# ─── Re-exportaciones por módulo ─────────────────────────────────────────────
from .views_auth import (
    home,
    redirect_por_rol,
    inicio,
    login_view,
    registro_view,
    completar_perfil,
    logout_view,
    forzar_cambio_password,
)
from .views_inspector import (
    panel_inspectores,
    verificar_vehiculo,
    registrar_infraccion,
    ticket_infraccion,
    gestion_infracciones,
    resumen_infracciones,
    pdf_infracciones_hoy,
    subcuadra_cercana,
    verificar_sia,
    cobrar_infraccion_inspector,
)
from .views_tesorero import (
    panel_tesorero,
    validar_rendicion,
    detalle_rendicion,
    depositar_comision,
    mis_liquidaciones_plataforma,
    crear_liquidacion_tesorero,
    gestionar_liquidacion_plataforma,
)
from .views_vendedor import (
    panel_vendedor,
    caja_inspector,
    consultar_deuda,
    ticket_pago_multa,
    registrar_estacionamiento_manual,
    registrar_estacionamiento_vendedor,
    resumen_cobros,
    ticket_cobro,
    cobrar_abono,
    resumen_caja,
    cobrar_infraccion_vendedor,
    cerrar_caja,
    mis_comisiones,
    certificar_comision,
    presentar_factura,
)
from .views_conductor import (
    inicio_usuarios,
    marcar_notificacion_leida,
    solicitar_verificacion,
    pagar_infraccion,
    agregar_vehiculo,
    eliminar_vehiculo,
    estacionar_vehiculo,
    subcuadra_cercana_conductor,
    historial_estacionamientos,
    renovar_estacionamiento,
    finalizar_estacionamiento,
    mis_infracciones,
    pagar_abono_conductor,
    crear_impugnacion,
    transferir_saldo,
    transferencias_saldo,
    responder_transferencia,
    solicitar_eliminacion_cuenta,
    cancelar_eliminacion_cuenta,
    enviar_sugerencia,
    mis_sugerencias,
)
from .views_admin import (
    panel_admin,
    dashboard_admin,
    inicio_admin,
    panel_exenciones,
    cargar_saldo,
    gestionar_inspectores,
    editar_inspector,
    gestionar_vendedores,
    editar_vendedor,
    gestionar_usuarios,
    detalle_usuario_admin,
    admin_infracciones,
    comprobante_infraccion,
    gestionar_tarifas,
    gestionar_horarios,
    gestionar_dias_especiales,
    admin_rendiciones,
    crear_rendicion,
    certificar_cierre,
    gestionar_verificaciones,
    resolver_verificacion,
    admin_vehiculos,
    admin_estacionamientos,
    historial_vendedor,
    crear_conductor,
    estadisticas_inspectores,
    estadisticas_inspectores_excel,
    pdf_infracciones_juzgado,
    pdf_rendicion,
    gestionar_subcuadras,
    importar_exenciones,
    auditoria_staff,
    reportes_subcuadras,
    vehiculos_exentos_sia,
    caja_vendedores,
    forzar_cierre_vendedor,
    mapa_calor_infracciones,
    admin_impugnaciones,
    resolver_impugnacion,
    gestionar_staff,
    editar_staff,
)
from .views_mp import (
    mp_iniciar_carga,
    mp_exitoso,
    mp_fallido,
    mp_pendiente,
    mp_webhook,
)

# ─── Utilidades generales ─────────────────────────────────────────────────────
from django.http import JsonResponse
from django.db import connection

def health_check(request):
    """
    Endpoint de health check para UptimeRobot y otros monitores de disponibilidad.
    Verifica que la app responda Y que la base de datos sea accesible.
    Devuelve 200 OK si todo está bien, 503 si hay un problema.
    """
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
        return JsonResponse({"status": "ok"}, status=200)
    except Exception as e:
        return JsonResponse({"status": "error", "detail": str(e)}, status=503)

# ─────────────────────────────────────────────
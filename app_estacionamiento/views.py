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
)
from .views_inspector import (
    panel_inspectores,
    verificar_vehiculo,
    registrar_infraccion,
    ticket_infraccion,
    gestion_infracciones,
    resumen_infracciones,
    pdf_infracciones_hoy,
)
from .views_tesorero import (
    panel_tesorero,
    validar_rendicion,
    depositar_comision,
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
)
from .views_conductor import (
    inicio_usuarios,
    marcar_notificacion_leida,
    solicitar_verificacion,
    pagar_infraccion,
    agregar_vehiculo,
    eliminar_vehiculo,
    estacionar_vehiculo,
    historial_estacionamientos,
    renovar_estacionamiento,
    finalizar_estacionamiento,
    mis_infracciones,
    pagar_abono_conductor,
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
)
from .views_mp import (
    mp_iniciar_carga,
    mp_exitoso,
    mp_fallido,
    mp_pendiente,
    mp_webhook,
)
# ─────────────────────────────────────────────
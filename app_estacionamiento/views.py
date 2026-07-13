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
    simular_pago,
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
# ─────────────────────────────────────────────────────────────────────────────

import logging
logger = logging.getLogger(__name__)

from django.conf import settings
from django.contrib import messages
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
from django.contrib.auth import authenticate, login, logout
from django.urls import reverse
from decimal import Decimal
from django.db import IntegrityError, transaction
from app_estacionamiento.use_cases.pagar_infraccion import ejecutar as pagar_infraccion_uc
from app_estacionamiento.services_caja import generar_cierre_caja
from app_estacionamiento.use_cases.cobrar_estacionamiento import ejecutar as cobrar_estacionamiento
from app_estacionamiento.use_cases.estacionar_vehiculo import ejecutar_estacionamiento
from .decorators import require_role, require_login
from .forms import RegistroUsuarioForm
from django.conf import settings
from django.contrib.auth.decorators import login_required
from .models import (
    Usuario,
    Vehiculo,
    VehiculoUsuario,
    Subcuadra,
    Estacionamiento,
    Infraccion,
    Municipio,
    MovimientoCaja,
    CierreCaja,
    Estado,
    VerificacionInspector,
    HorarioEstacionamiento,
    DiaEspecial,
    SolicitudVerificacion,
    Notificacion,
    AbonoMensual,
    Rendicion,
    LiquidacionComision,
    TIPOS_EXENCION,
)

from .utils import (
    get_subcuadra_default,
    puede_estacionar_ahora,
    calcular_opciones_duracion,
    cerrar_estacionamientos_vencidos_por_horario,
)
from .factories import EstacionamientoFactory
from datetime import timedelta
from django.db.models import Count, Sum, Q
from django.db.models.functions import TruncDate
from app_estacionamiento.services_verificacion import verificar_estado_vehiculo
from app_estacionamiento.services_infracciones import crear_infraccion, ErrorInfraccion
from app_estacionamiento.use_cases.finalizar_estacionamiento import ( ejecutar as finalizar_estacionamiento_uc)
from django.core.mail import send_mail



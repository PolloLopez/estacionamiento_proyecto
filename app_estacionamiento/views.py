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
#
# Próximos módulos (pendiente):
#   views_mp.py

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


# =========================================================
# VIEWS LOGIN / LOGOUT
# =========================================================
# =========================================================
# =========================================================
# VIEWS MERCADOPAGO - CARGA DE SALDO
# =========================================================

@require_login
def mp_iniciar_carga(request):
    """
    Paso 1: el conductor elige el monto y se crea una preferencia en MercadoPago.
    MP devuelve una URL de checkout a la que redirigimos al usuario.
    """
    import mercadopago

    if request.method != "POST":
        return render(request, "usuarios/mp_cargar_saldo.html", {
            "montos_rapidos": [500, 1000, 2000, 5000],
        })

    monto_str = request.POST.get("monto", "")
    try:
        monto = int(monto_str)
        if monto <= 0:
            raise ValueError()
    except (ValueError, TypeError):
        messages.error(request, "Ingresa un monto valido mayor a 0.")
        return render(request, "usuarios/mp_cargar_saldo.html")

    access_token = settings.MP_ACCESS_TOKEN
    if not access_token:
        messages.error(request, "MercadoPago no esta configurado en este entorno.")
        return render(request, "usuarios/mp_cargar_saldo.html")

    sdk = mercadopago.SDK(access_token)

    # La URL base del sitio (necesaria para los callbacks de MP)
    # En Railway, el proxy termina el SSL y puede no pasar HTTP_X_FORWARDED_PROTO
    # en tiempo de procesar MP. Forzamos HTTPS en producción para que MP acepte
    # las back_urls (auto_return requiere HTTPS obligatoriamente).
    base_url = request.build_absolute_uri("/").rstrip("/")
    if not settings.DEBUG:
        base_url = base_url.replace("http://", "https://")

    preferencia = {
        "items": [
            {
                "title": "Carga de saldo - Estacionamiento",
                "quantity": 1,
                "unit_price": float(monto),
                "currency_id": "ARS",
            }
        ],
        "back_urls": {
            "success": f"{base_url}/usuarios/mp/exitoso/",
            "failure": f"{base_url}/usuarios/mp/fallido/",
            "pending": f"{base_url}/usuarios/mp/pendiente/",
        },
        # auto_return eliminado: requería back_urls en HTTPS estricto y daba
        # error 400 "auto_return invalid". El webhook + back_urls alcanzan.
        # El webhook recibe notificaciones de MP (asincrono)
        "notification_url": f"{base_url}/usuarios/mp/webhook/",
        # Metadatos para identificar al usuario en el webhook
        "metadata": {
            "usuario_id": str(request.user.id),
            "monto": str(monto),
        },
        "external_reference": f"usuario_{request.user.id}_monto_{monto}",
    }

    resultado = sdk.preference().create(preferencia)

    if resultado["status"] not in (200, 201):
        # Loguear el error completo de MP para diagnóstico en Railway logs
        logger.error(
            "MercadoPago error al crear preferencia | status=%s | response=%s | usuario=%s",
            resultado.get("status"),
            resultado.get("response"),
            request.user.id,
        )
        # Mostrar detalle del error en DEBUG para facilitar diagnóstico
        if settings.DEBUG:
            detalle = resultado.get("response", {})
            messages.error(request, f"Error MP ({resultado.get('status')}): {detalle}")
        else:
            messages.error(request, "No se pudo crear la preferencia de pago. Revisá los logs del servidor.")
        return render(request, "usuarios/mp_cargar_saldo.html", {
            "montos_rapidos": [500, 1000, 2000, 5000],
        })

    respuesta_mp = resultado["response"]

    # Detectar si el request viene de un dispositivo mobile.
    # En mobile usamos mobile_init_point: abre la app de MercadoPago si está instalada,
    # y cae al browser como fallback. En desktop usamos init_point (web).
    user_agent = request.META.get("HTTP_USER_AGENT", "").lower()
    es_mobile = any(kw in user_agent for kw in (
        "android", "iphone", "ipad", "ipod", "mobile", "blackberry", "windows phone"
    ))

    if settings.MP_SANDBOX:
        # Sandbox: solo tiene sandbox_init_point (sin mobile)
        checkout_url = respuesta_mp.get("sandbox_init_point", "")
    elif es_mobile and respuesta_mp.get("mobile_init_point"):
        # Producción mobile: abre la app de MercadoPago si está instalada
        checkout_url = respuesta_mp["mobile_init_point"]
    else:
        # Producción desktop
        checkout_url = respuesta_mp.get("init_point", "")

    if not checkout_url:
        messages.error(request, "No se pudo obtener la URL de pago de MercadoPago.")
        return render(request, "usuarios/mp_cargar_saldo.html", {
            "montos_rapidos": [500, 1000, 2000, 5000],
        })

    return redirect(checkout_url)


@require_login
def mp_exitoso(request):
    """
    MP redirige aquí después de un pago aprobado.

    SEGURIDAD: NO confiamos en los parámetros GET (monto, estado).
    Consultamos la API de MP con el payment_id para obtener el monto real.
    El webhook también acredita de forma asíncrona como respaldo.
    """
    import mercadopago
    from decimal import Decimal
    from app_estacionamiento.use_cases.acreditar_saldo_mp import ejecutar as acreditar

    payment_id = request.GET.get("payment_id", "").strip()

    if not payment_id:
        messages.warning(request, "No se recibió confirmación del pago.")
        return render(request, "usuarios/mp_resultado.html", {"estado": "fallido"})

    # Verificar el pago directamente con la API de MP
    try:
        sdk = mercadopago.SDK(settings.MP_ACCESS_TOKEN)
        resultado = sdk.payment().get(payment_id)

        if resultado["status"] != 200:
            raise Exception("MP no devolvió el pago")

        info = resultado["response"]

        if info.get("status") != "approved":
            messages.warning(request, "El pago aún no fue acreditado por MercadoPago.")
            return render(request, "usuarios/mp_resultado.html", {"estado": "pendiente"})

        # Verificar que el pago le pertenece a este usuario
        metadata = info.get("metadata", {})
        usuario_id_mp = str(metadata.get("usuario_id", ""))
        if usuario_id_mp and usuario_id_mp != str(request.user.id):
            # El pago no corresponde a este usuario — no acreditar
            messages.error(request, "Error de validación del pago.")
            return render(request, "usuarios/mp_resultado.html", {"estado": "fallido"})

        # Monto real desde la API (no desde la URL)
        monto = Decimal(str(info.get("transaction_amount", 0)))
        if monto <= 0:
            raise Exception("Monto inválido en la respuesta de MP")

    except Exception as e:
        # Si falla la verificación, el webhook igual acreditará
        messages.warning(
            request,
            "Tu pago fue procesado. Si no ves el saldo en unos minutos, contactá soporte."
        )
        return render(request, "usuarios/mp_resultado.html", {"estado": "pendiente"})

    try:
        acreditar(request.user, monto, payment_id)
    except Exception:
        # Si ya fue acreditado por el webhook, esta bien
        pass

    # Refrescar saldo desde la DB y redirigir al inicio con mensaje
    request.user.refresh_from_db()
    messages.success(request, f"✅ Se acreditaron ${monto} a tu saldo. Nuevo saldo: ${request.user.saldo}")
    return redirect("inicio_usuarios")


@require_login
def mp_fallido(request):
    messages.error(request, "El pago fue rechazado o cancelado. No se realizó ningún cobro.")
    return redirect("mp_iniciar_carga")


@require_login
def mp_pendiente(request):
    messages.warning(request, "El pago está siendo procesado. El saldo se acreditará automáticamente cuando se confirme.")
    return redirect("inicio_usuarios")


from django.views.decorators.csrf import csrf_exempt
from django.http import HttpResponse

@csrf_exempt
def mp_webhook(request):
    """
    Webhook que MercadoPago llama de forma asincrona para notificar pagos.
    Se ejecuta independientemente de que el usuario haya vuelto al sitio o no.
    Esto garantiza que el saldo se acredite aunque el usuario cierre el browser.
    """
    import json
    from decimal import Decimal
    from app_estacionamiento.use_cases.acreditar_saldo_mp import ejecutar as acreditar

    if request.method != "POST":
        return HttpResponse(status=200)

    try:
        data = json.loads(request.body)
    except Exception:
        return HttpResponse(status=200)

    # MP envia tipo "payment" para pagos
    if data.get("type") != "payment":
        return HttpResponse(status=200)

    payment_id = str(data.get("data", {}).get("id", ""))
    if not payment_id:
        return HttpResponse(status=200)

    # Consultamos el detalle del pago a la API de MP
    import mercadopago
    sdk = mercadopago.SDK(settings.MP_ACCESS_TOKEN)
    pago = sdk.payment().get(payment_id)

    if pago["status"] != 200:
        return HttpResponse(status=200)

    info = pago["response"]

    if info.get("status") != "approved":
        return HttpResponse(status=200)

    # Recuperamos usuario desde metadata y monto desde transaction_amount (más seguro)
    try:
        metadata = info.get("metadata", {})
        usuario_id = metadata.get("usuario_id")
        # Usar transaction_amount (monto real procesado por MP) en vez del metadata
        # (por consistencia con mp_exitoso y para resistir cambios de promociones de MP)
        monto = Decimal(str(info.get("transaction_amount", metadata.get("monto", 0))))
        usuario = Usuario.objects.get(pk=usuario_id)
    except Exception:
        return HttpResponse(status=200)

    try:
        acreditar(usuario, monto, payment_id)
    except Exception:
        pass  # Si ya fue acreditado (idempotencia) no hay problema

    return HttpResponse(status=200)



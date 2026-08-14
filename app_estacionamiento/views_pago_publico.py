# app_estacionamiento/views_pago_publico.py
"""
Vistas de pago público (sin registro de usuario).

Permite pagar infracciones, estacionar y contratar abonos mensuales
directamente con MercadoPago, sin necesidad de crear una cuenta.

Acceso: público (no requiere @login_required ni @require_role).

Flujo por tipo:
  Infracción:
    1. GET /pagar/<patente>/        → detalle_patente muestra las infracciones
    2. POST /pagar/infraccion/<id>/ → iniciar_pago_infraccion crea PagoPublico + preferencia MP
    3. MP redirige a mp_exitoso_publico → procesa_pago_publico → infracción marcada como pagada

  Estacionamiento:
    1. GET /pagar/                  → buscar_patente (formulario de patente)
    2. GET /pagar/<patente>/        → detalle_patente con formulario de estacionamiento
    3. POST /pagar/estacionar/      → iniciar_pago_estacionamiento
    4. MP redirige a mp_exitoso_publico → crea Estacionamiento

  Abono:
    1. GET /pagar/<patente>/        → detalle_patente con formulario de abono
    2. POST /pagar/abono/           → iniciar_pago_abono
    3. MP redirige a mp_exitoso_publico → crea AbonoMensual
"""

import json
import logging
from datetime import date
from decimal import Decimal

from django.conf import settings
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone

from .models import (
    Infraccion, Municipio, PagoPublico, Subcuadra, Tarifa, Vehiculo,
    AbonoMensual, Estacionamiento,
)
from .services.horarios import obtener_tarifa_hora
from .use_cases.procesar_pago_publico import ejecutar as procesar_pago_publico
from .utils import sanitizar_patente

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# Helpers internos
# ─────────────────────────────────────────────────────────────────────────────

def _get_municipio():
    """
    Devuelve el primer municipio activo.
    Para deployments multi-municipio, extender para recibir el ID por URL.
    """
    return Municipio.objects.filter(activo=True).first()


def _crear_preferencia_mp(request, pago: PagoPublico, titulo: str) -> str | None:
    """
    Crea una preferencia de MercadoPago para el PagoPublico dado.
    Devuelve la URL de checkout, o None si falla.

    La preferencia incluye pago_publico_id en metadata para que el webhook
    sepa a qué PagoPublico corresponde la notificación.
    """
    import mercadopago

    access_token = settings.MP_ACCESS_TOKEN
    if not access_token:
        return None

    sdk = mercadopago.SDK(access_token)

    # URLs de retorno para el usuario
    base = request.build_absolute_uri
    preferencia = {
        "items": [
            {
                "title":      titulo,
                "quantity":   1,
                "unit_price": float(pago.monto),
                "currency_id": "ARS",
            }
        ],
        "back_urls": {
            "success": base(reverse("pago_publico_mp_exitoso")),
            "failure": base(reverse("pago_publico_mp_fallido")),
            "pending": base(reverse("pago_publico_mp_pendiente")),
        },
        # Webhook comparte el endpoint existente de MP; detecta pago_publico_id en metadata
        "notification_url": base(reverse("mp_webhook")),
        "metadata": {
            "pago_publico_id": str(pago.id),
            "tipo":            pago.tipo,
            "patente":         pago.patente,
        },
        "external_reference": f"pago_publico_{pago.id}",
    }

    resultado = sdk.preference().create(preferencia)

    if resultado["status"] not in (200, 201):
        logger.error(
            "MP error creando preferencia pública | status=%s | pago_id=%s | response=%s",
            resultado.get("status"),
            pago.id,
            resultado.get("response"),
        )
        return None

    respuesta_mp = resultado["response"]
    pago.mp_preference_id = respuesta_mp.get("id", "")
    pago.save(update_fields=["mp_preference_id"])

    # Elegir punto de entrada según dispositivo y entorno
    user_agent = request.META.get("HTTP_USER_AGENT", "").lower()
    es_mobile  = any(kw in user_agent for kw in ("android", "iphone", "ipad", "mobile"))

    if settings.MP_SANDBOX:
        return respuesta_mp.get("sandbox_init_point", "")
    elif es_mobile and respuesta_mp.get("mobile_init_point"):
        return respuesta_mp["mobile_init_point"]
    return respuesta_mp.get("init_point", "")


# ─────────────────────────────────────────────────────────────────────────────
# Buscador de patente (punto de entrada para estacionamiento y abono)
# ─────────────────────────────────────────────────────────────────────────────

def buscar_patente(request):
    """
    GET: muestra formulario de búsqueda por patente.
    POST: redirige a detalle_patente con la patente ingresada.
    """
    if request.method == "POST":
        patente = sanitizar_patente(request.POST.get("patente", ""))
        if patente:
            return redirect("pago_publico_detalle", patente=patente)

    return render(request, "pago_publico/buscar.html")


# ─────────────────────────────────────────────────────────────────────────────
# Detalle por patente: infracciones + opciones
# ─────────────────────────────────────────────────────────────────────────────

def detalle_patente(request, patente):
    """
    Muestra las infracciones pendientes de una patente y las opciones de pago:
    - Pagar cada infracción pendiente por MercadoPago
    - Estacionar ahora (requiere subcuadra y duración)
    - Contratar abono mensual

    No requiere que el vehículo exista en el sistema: si la patente no tiene
    historial, igual puede estacionar o contratar abono.
    """
    patente    = sanitizar_patente(patente)
    municipio  = _get_municipio()

    if not municipio:
        return render(request, "pago_publico/error.html", {
            "mensaje": "No hay municipios activos configurados."
        })

    # Infracciones pendientes para esta patente en este municipio
    infracciones_pendientes = Infraccion.objects.filter(
        vehiculo__patente=patente,
        municipio=municipio,
        estado="pendiente",
    ).order_by("-creado_en")

    # Estacionamiento activo (para mostrar advertencia)
    estacionamiento_activo = Estacionamiento.objects.filter(
        vehiculo__patente=patente,
        estado="activo",
    ).first()

    # Abono activo en el mes actual
    hoy        = timezone.localdate()
    mes_actual = date(hoy.year, hoy.month, 1)
    abono_activo = AbonoMensual.objects.filter(
        vehiculo__patente=patente,
        municipio=municipio,
        mes=mes_actual,
    ).first()

    # Mes siguiente para ofrecer abono
    if hoy.month == 12:
        mes_siguiente = date(hoy.year + 1, 1, 1)
    else:
        mes_siguiente = date(hoy.year, hoy.month + 1, 1)

    # Subcuadras del municipio para el selector de estacionamiento
    subcuadras = Subcuadra.objects.filter(municipio=municipio).order_by("calle", "altura")

    # Tarifa vigente para calcular costos en el frontend
    tarifa = Tarifa.objects.filter(municipio=municipio).first()

    return render(request, "pago_publico/detalle_patente.html", {
        "patente":                 patente,
        "municipio":               municipio,
        "infracciones_pendientes": infracciones_pendientes,
        "estacionamiento_activo":  estacionamiento_activo,
        "abono_activo":            abono_activo,
        "mes_actual":              mes_actual,
        "mes_siguiente":           mes_siguiente,
        "subcuadras":              subcuadras,
        "tarifa":                  tarifa,
        # Precios formateados para JS
        "tarifa_auto_json":        json.dumps(float(tarifa.precio_por_hora)) if tarifa else "0",
        "tarifa_moto_json":        json.dumps(float(tarifa.precio_por_hora_moto)) if tarifa and hasattr(tarifa, 'precio_por_hora_moto') else "0",
        "precio_abono_auto_json":  json.dumps(float(tarifa.precio_abono_auto)) if tarifa else "0",
        "precio_abono_moto_json":  json.dumps(float(tarifa.precio_abono_moto)) if tarifa else "0",
    })


# ─────────────────────────────────────────────────────────────────────────────
# Iniciar pago de infracción
# ─────────────────────────────────────────────────────────────────────────────

def iniciar_pago_infraccion(request, infraccion_id):
    """
    POST: crea un PagoPublico y redirige al checkout de MP para pagar la infracción.
    Valida que la infracción exista y esté pendiente antes de crear la preferencia.
    """
    if request.method != "POST":
        return redirect("pago_publico_buscar")

    municipio = _get_municipio()
    infraccion = get_object_or_404(Infraccion, pk=infraccion_id, estado="pendiente")

    # Validar que la infracción pertenece al municipio activo
    if infraccion.municipio != municipio:
        return render(request, "pago_publico/error.html", {
            "mensaje": "No se encontró la infracción."
        })

    email = (request.POST.get("email") or "").strip()

    pago = PagoPublico.objects.create(
        tipo          = "infraccion",
        municipio     = municipio,
        patente       = infraccion.vehiculo.patente,
        monto         = infraccion.monto,
        email_contacto= email,
        infraccion    = infraccion,
    )

    checkout_url = _crear_preferencia_mp(
        request, pago,
        titulo=f"Infracción {infraccion.vehiculo.patente} — ${infraccion.monto}"
    )

    if not checkout_url:
        pago.estado = "fallido"
        pago.save(update_fields=["estado"])
        return render(request, "pago_publico/error.html", {
            "mensaje": "No se pudo conectar con MercadoPago. Intentá de nuevo."
        })

    return redirect(checkout_url)


# ─────────────────────────────────────────────────────────────────────────────
# Iniciar pago de estacionamiento
# ─────────────────────────────────────────────────────────────────────────────

def iniciar_pago_estacionamiento(request):
    """
    POST: valida patente + subcuadra + duración, calcula el costo y redirige a MP.
    """
    if request.method != "POST":
        return redirect("pago_publico_buscar")

    patente    = sanitizar_patente(request.POST.get("patente", ""))
    municipio  = _get_municipio()

    if not patente or not municipio:
        return render(request, "pago_publico/error.html", {
            "mensaje": "Datos incompletos."
        })

    # Validar subcuadra
    subcuadra_id = request.POST.get("subcuadra_id", "")
    try:
        subcuadra = Subcuadra.objects.get(pk=int(subcuadra_id), municipio=municipio)
    except (Subcuadra.DoesNotExist, ValueError, TypeError):
        return render(request, "pago_publico/error.html", {
            "mensaje": "Subcuadra no válida."
        })

    # Validar duración
    try:
        duracion = Decimal(request.POST.get("duracion_horas", ""))
        if duracion <= 0:
            raise ValueError()
    except (ValueError, TypeError):
        return render(request, "pago_publico/error.html", {
            "mensaje": "Duración no válida."
        })

    # Verificar que no tenga estacionamiento activo
    if Estacionamiento.objects.filter(vehiculo__patente=patente, estado="activo").exists():
        return render(request, "pago_publico/error.html", {
            "mensaje": f"La patente {patente} ya tiene un estacionamiento activo."
        })

    # Calcular costo según tarifa
    tipo_vehiculo = request.POST.get("tipo_vehiculo", "auto")
    tarifa = Tarifa.objects.filter(municipio=municipio).first()
    vehiculo_mock = type("V", (), {"tipo": tipo_vehiculo})()  # objeto duck-typing para obtener_tarifa_hora
    tarifa_hora   = obtener_tarifa_hora(tarifa, vehiculo_mock) if tarifa else Decimal("0")
    monto         = duracion * tarifa_hora

    if monto <= 0:
        return render(request, "pago_publico/error.html", {
            "mensaje": "No hay tarifa configurada para este municipio."
        })

    email = (request.POST.get("email") or "").strip()

    pago = PagoPublico.objects.create(
        tipo           = "estacionamiento",
        municipio      = municipio,
        patente        = patente,
        monto          = monto,
        email_contacto = email,
        subcuadra      = subcuadra,
        duracion_horas = duracion,
    )

    checkout_url = _crear_preferencia_mp(
        request, pago,
        titulo=f"Estacionamiento {patente} — {duracion}h en {subcuadra}"
    )

    if not checkout_url:
        pago.estado = "fallido"
        pago.save(update_fields=["estado"])
        return render(request, "pago_publico/error.html", {
            "mensaje": "No se pudo conectar con MercadoPago. Intentá de nuevo."
        })

    return redirect(checkout_url)


# ─────────────────────────────────────────────────────────────────────────────
# Iniciar pago de abono mensual
# ─────────────────────────────────────────────────────────────────────────────

def iniciar_pago_abono(request):
    """
    POST: verifica que no haya abono vigente para ese mes, calcula el precio y
    redirige a MP.
    """
    if request.method != "POST":
        return redirect("pago_publico_buscar")

    patente   = sanitizar_patente(request.POST.get("patente", ""))
    municipio = _get_municipio()

    if not patente or not municipio:
        return render(request, "pago_publico/error.html", {
            "mensaje": "Datos incompletos."
        })

    # Parsear el mes elegido ("2026-08" → date(2026, 8, 1))
    mes_str = request.POST.get("mes_abono", "")
    try:
        anio, mes = mes_str.split("-")
        mes_abono = date(int(anio), int(mes), 1)
    except Exception:
        return render(request, "pago_publico/error.html", {
            "mensaje": "Mes no válido."
        })

    # Verificar abono duplicado
    if AbonoMensual.objects.filter(
        vehiculo__patente=patente, municipio=municipio, mes=mes_abono
    ).exists():
        return render(request, "pago_publico/error.html", {
            "mensaje": f"La patente {patente} ya tiene abono para ese mes."
        })

    # Precio según tipo de vehículo
    tipo_vehiculo = request.POST.get("tipo_vehiculo", "auto")
    tarifa = Tarifa.objects.filter(municipio=municipio).first()
    if not tarifa:
        return render(request, "pago_publico/error.html", {
            "mensaje": "No hay tarifa configurada para este municipio."
        })

    monto = tarifa.precio_abono_auto if tipo_vehiculo == "auto" else tarifa.precio_abono_moto

    if not monto or monto <= 0:
        return render(request, "pago_publico/error.html", {
            "mensaje": "No hay precio de abono configurado."
        })

    email = (request.POST.get("email") or "").strip()

    # Nombre del mes en español para el título de MP
    MESES_ES = {
        1: "enero", 2: "febrero", 3: "marzo", 4: "abril",
        5: "mayo", 6: "junio", 7: "julio", 8: "agosto",
        9: "septiembre", 10: "octubre", 11: "noviembre", 12: "diciembre",
    }
    nombre_mes = MESES_ES.get(mes_abono.month, str(mes_abono.month))

    pago = PagoPublico.objects.create(
        tipo           = "abono",
        municipio      = municipio,
        patente        = patente,
        monto          = monto,
        email_contacto = email,
        mes_abono      = mes_abono,
    )

    checkout_url = _crear_preferencia_mp(
        request, pago,
        titulo=f"Abono {nombre_mes} {mes_abono.year} — {patente}"
    )

    if not checkout_url:
        pago.estado = "fallido"
        pago.save(update_fields=["estado"])
        return render(request, "pago_publico/error.html", {
            "mensaje": "No se pudo conectar con MercadoPago. Intentá de nuevo."
        })

    return redirect(checkout_url)


# ─────────────────────────────────────────────────────────────────────────────
# API pública: subcuadra más cercana (versión sin login para pago público)
# ─────────────────────────────────────────────────────────────────────────────

def subcuadra_cercana_publica(request):
    """
    GET ?lat=<float>&lon=<float>[&municipio_id=<int>]
    Devuelve la subcuadra más cercana en formato JSON.
    Versión sin autenticación del mismo endpoint del inspector.
    """
    try:
        lat = float(request.GET.get("lat"))
        lon = float(request.GET.get("lon"))
    except (TypeError, ValueError):
        return JsonResponse({"error": "Coordenadas inválidas"}, status=400)

    municipio = _get_municipio()
    if not municipio:
        return JsonResponse({})

    subcuadras = Subcuadra.objects.filter(
        municipio=municipio,
        lat__isnull=False,
        lon__isnull=False,
    )

    if not subcuadras.exists():
        return JsonResponse({})

    mas_cercana = min(subcuadras, key=lambda s: (s.lat - lat) ** 2 + (s.lon - lon) ** 2)
    return JsonResponse({
        "id":     mas_cercana.id,
        "nombre": str(mas_cercana),
        "calle":  mas_cercana.calle,
        "altura": mas_cercana.altura,
    })


# ─────────────────────────────────────────────────────────────────────────────
# Callbacks de MercadoPago
# ─────────────────────────────────────────────────────────────────────────────

def mp_exitoso_publico(request):
    """
    MP redirige aquí después de un pago aprobado en el flujo público.

    Recupera el PagoPublico por preference_id (que MP incluye en la URL como
    ?preference_id=...) y lo procesa si no fue procesado ya por el webhook.
    """
    import mercadopago

    payment_id    = request.GET.get("payment_id", "").strip()
    preference_id = request.GET.get("preference_id", "").strip()

    # Buscar el PagoPublico por preferencia o por payment_id si ya procesó el webhook
    pago = (
        PagoPublico.objects.filter(mp_preference_id=preference_id).first()
        or PagoPublico.objects.filter(mp_payment_id=payment_id).first()
    )

    if not pago:
        return render(request, "pago_publico/resultado.html", {
            "estado":  "pendiente",
            "mensaje": "Tu pago está siendo procesado. Guardá el número de operación.",
            "payment_id": payment_id,
        })

    # Si el webhook ya lo procesó, mostrar resultado directo
    if pago.estado == "aprobado":
        return render(request, "pago_publico/resultado.html", {
            "estado": "aprobado",
            "pago":   pago,
        })

    # Sino, verificar con la API de MP y procesar
    if not payment_id:
        return render(request, "pago_publico/resultado.html", {
            "estado":  "pendiente",
            "mensaje": "Tu pago está siendo procesado por MercadoPago.",
            "pago":    pago,
        })

    try:
        sdk      = mercadopago.SDK(settings.MP_ACCESS_TOKEN)
        resultado = sdk.payment().get(payment_id)

        if resultado["status"] != 200:
            raise Exception("MP no devolvió el pago")

        info = resultado["response"]
        if info.get("status") != "approved":
            return render(request, "pago_publico/resultado.html", {
                "estado":  "pendiente",
                "mensaje": "El pago todavía no fue confirmado por MercadoPago.",
                "pago":    pago,
            })

        monto = Decimal(str(info.get("transaction_amount", 0)))
        procesar_pago_publico(pago.id, payment_id, monto)
        pago.refresh_from_db()

    except Exception:
        return render(request, "pago_publico/resultado.html", {
            "estado":  "pendiente",
            "mensaje": "Tu pago fue procesado. Si no se refleja en unos minutos, guardá el número de operación.",
            "pago":    pago,
            "payment_id": payment_id,
        })

    return render(request, "pago_publico/resultado.html", {
        "estado": "aprobado",
        "pago":   pago,
    })


def mp_fallido_publico(request):
    """MP redirige aquí cuando el pago fue rechazado o cancelado."""
    preference_id = request.GET.get("preference_id", "").strip()
    pago = PagoPublico.objects.filter(mp_preference_id=preference_id).first()

    if pago and pago.estado == "pendiente":
        pago.estado = "fallido"
        pago.save(update_fields=["estado"])

    return render(request, "pago_publico/resultado.html", {
        "estado":  "fallido",
        "mensaje": "El pago fue rechazado o cancelado. No se realizó ningún cobro.",
        "pago":    pago,
    })


def mp_pendiente_publico(request):
    """MP redirige aquí cuando el pago está en proceso (transferencias, etc.)."""
    preference_id = request.GET.get("preference_id", "").strip()
    pago = PagoPublico.objects.filter(mp_preference_id=preference_id).first()

    return render(request, "pago_publico/resultado.html", {
        "estado":  "pendiente",
        "mensaje": "Tu pago está siendo procesado. Se acreditará automáticamente cuando se confirme.",
        "pago":    pago,
    })


# ─────────────────────────────────────────────────────────────────────────────
# Landing page del sistema (alojada en la app, sin login)
# ─────────────────────────────────────────────────────────────────────────────

def landing_sistema(request):
    """
    Página de presentación del sistema, accesible sin login.
    Se sirve desde la propia app para no depender de GitHub Pages.
    """
    return render(request, "landing.html")

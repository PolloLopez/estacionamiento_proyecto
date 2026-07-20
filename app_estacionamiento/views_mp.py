# app_estacionamiento/views_mp.py
"""
Vistas de integración con MercadoPago.

Responsabilidades:
- Iniciar el flujo de carga de saldo (crear preferencia en MP)
- Recibir el callback de pago exitoso y acreditar el saldo
- Manejar callbacks de pago fallido y pendiente
- Procesar el webhook asíncrono de MP (idempotente)

Flujo completo:
  conductor → mp_iniciar_carga → [checkout MP] → mp_exitoso / mp_fallido / mp_pendiente
  MP (asíncrono) → mp_webhook → acreditar_saldo_mp

SEGURIDAD:
  - mp_exitoso NO confía en los parámetros GET; consulta la API de MP con el payment_id.
  - mp_webhook verifica que el pago sea de tipo "payment" y estado "approved" antes de acreditar.
  - La acreditación (use_case acreditar_saldo_mp) es idempotente: no acredita dos veces el mismo pago.
"""

import json
import logging
from decimal import Decimal

from django.conf import settings
from django.contrib import messages
from django.http import HttpResponse
from django.shortcuts import redirect, render
from django.views.decorators.csrf import csrf_exempt

from .decorators import require_login
from .models import Usuario

logger = logging.getLogger(__name__)


@require_login
def mp_iniciar_carga(request):
    """
    Paso 1: el conductor elige el monto y se crea una preferencia en MercadoPago.
    MP devuelve una URL de checkout a la que redirigimos al usuario.

    GET  → muestra el formulario con montos rápidos sugeridos.
    POST → crea la preferencia y redirige al checkout de MP.
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

    # La URL base del sitio (necesaria para los callbacks de MP).
    # En Railway, el proxy termina el SSL. Forzamos HTTPS en producción
    # porque MP requiere HTTPS estricto en back_urls.
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
        # auto_return eliminado: requería back_urls HTTPS estricto y daba
        # error 400 "auto_return invalid". El webhook + back_urls alcanzan.
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
        # Logueamos el error completo para diagnóstico en Railway
        logger.error(
            "MercadoPago error al crear preferencia | status=%s | response=%s | usuario=%s",
            resultado.get("status"),
            resultado.get("response"),
            request.user.id,
        )
        if settings.DEBUG:
            detalle = resultado.get("response", {})
            messages.error(request, f"Error MP ({resultado.get('status')}): {detalle}")
        else:
            messages.error(
                request,
                "No se pudo crear la preferencia de pago. Revisá los logs del servidor.",
            )
        return render(request, "usuarios/mp_cargar_saldo.html", {
            "montos_rapidos": [500, 1000, 2000, 5000],
        })

    respuesta_mp = resultado["response"]

    # Detectar dispositivo para elegir el init_point correcto.
    # mobile_init_point abre la app de MP si está instalada; init_point abre el web.
    user_agent = request.META.get("HTTP_USER_AGENT", "").lower()
    es_mobile   = any(kw in user_agent for kw in (
        "android", "iphone", "ipad", "ipod", "mobile", "blackberry", "windows phone"
    ))

    if settings.MP_SANDBOX:
        # Sandbox solo tiene sandbox_init_point (sin variante mobile)
        checkout_url = respuesta_mp.get("sandbox_init_point", "")
    elif es_mobile and respuesta_mp.get("mobile_init_point"):
        checkout_url = respuesta_mp["mobile_init_point"]
    else:
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
    from app_estacionamiento.use_cases.acreditar_saldo_mp import ejecutar as acreditar

    payment_id = request.GET.get("payment_id", "").strip()

    if not payment_id:
        messages.warning(request, "No se recibió confirmación del pago.")
        return render(request, "usuarios/mp_resultado.html", {"estado": "fallido"})

    try:
        sdk      = mercadopago.SDK(settings.MP_ACCESS_TOKEN)
        resultado = sdk.payment().get(payment_id)

        if resultado["status"] != 200:
            raise Exception("MP no devolvió el pago")

        info = resultado["response"]

        if info.get("status") != "approved":
            messages.warning(request, "El pago aún no fue acreditado por MercadoPago.")
            return render(request, "usuarios/mp_resultado.html", {"estado": "pendiente"})

        # Verificar que el pago le pertenece a este usuario
        metadata      = info.get("metadata", {})
        usuario_id_mp = str(metadata.get("usuario_id", ""))
        if usuario_id_mp and usuario_id_mp != str(request.user.id):
            messages.error(request, "Error de validación del pago.")
            return render(request, "usuarios/mp_resultado.html", {"estado": "fallido"})

        # Monto real desde la API (no desde la URL)
        monto = Decimal(str(info.get("transaction_amount", 0)))
        if monto <= 0:
            raise Exception("Monto inválido en la respuesta de MP")

    except Exception:
        # Si falla la verificación, el webhook igual acreditará
        messages.warning(
            request,
            "Tu pago fue procesado. Si no ves el saldo en unos minutos, contactá soporte.",
        )
        return render(request, "usuarios/mp_resultado.html", {"estado": "pendiente"})

    try:
        acreditar(request.user, monto, payment_id)
    except Exception:
        pass  # Si ya fue acreditado por el webhook, está bien

    request.user.refresh_from_db()
    messages.success(
        request,
        f"✅ Se acreditaron ${monto} a tu saldo. Nuevo saldo: ${request.user.saldo}",
    )
    return redirect("inicio_usuarios")


@require_login
def mp_fallido(request):
    """MP redirige aquí cuando el pago fue rechazado o cancelado."""
    messages.error(request, "El pago fue rechazado o cancelado. No se realizó ningún cobro.")
    return redirect("mp_iniciar_carga")


@require_login
def mp_pendiente(request):
    """MP redirige aquí cuando el pago está en proceso (transferencias, efectivo, etc.)."""
    messages.warning(
        request,
        "El pago está siendo procesado. El saldo se acreditará automáticamente cuando se confirme.",
    )
    return redirect("inicio_usuarios")


@csrf_exempt
def mp_webhook(request):
    """
    Webhook que MercadoPago llama de forma asíncrona para notificar pagos.
    Se ejecuta independientemente de que el usuario haya vuelto al sitio o no.
    Garantiza que el saldo se acredite aunque el conductor cierre el browser.

    La acreditación es idempotente: si mp_exitoso ya acreditó, este no duplica.
    Siempre responde 200 para que MP no reintente indefinidamente.
    """
    import mercadopago
    from app_estacionamiento.use_cases.acreditar_saldo_mp import ejecutar as acreditar

    if request.method != "POST":
        return HttpResponse(status=200)

    try:
        data = json.loads(request.body)
    except Exception:
        return HttpResponse(status=200)

    # MP envía tipo "payment" para pagos; otros tipos se ignoran
    if data.get("type") != "payment":
        return HttpResponse(status=200)

    payment_id = str(data.get("data", {}).get("id", ""))
    if not payment_id:
        return HttpResponse(status=200)

    # Consultar el detalle del pago directamente a la API de MP
    sdk  = mercadopago.SDK(settings.MP_ACCESS_TOKEN)
    pago = sdk.payment().get(payment_id)

    if pago["status"] != 200:
        return HttpResponse(status=200)

    info = pago["response"]

    if info.get("status") != "approved":
        return HttpResponse(status=200)

    # Recuperar usuario y monto desde la respuesta de MP (no desde metadata directamente)
    # transaction_amount es el monto real procesado; más seguro que el metadata enviado en la preferencia
    try:
        metadata   = info.get("metadata", {})
        usuario_id = metadata.get("usuario_id")
        monto      = Decimal(str(info.get("transaction_amount", metadata.get("monto", 0))))
        usuario    = Usuario.objects.get(pk=usuario_id)
    except Exception:
        return HttpResponse(status=200)

    try:
        acreditar(usuario, monto, payment_id)
    except Exception:
        pass  # Idempotencia: si ya fue acreditado, no hay problema

    return HttpResponse(status=200)

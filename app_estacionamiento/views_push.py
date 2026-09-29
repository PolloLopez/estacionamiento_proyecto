# app_estacionamiento/views_push.py
"""
Endpoints para la Push API del navegador (Web Push / VAPID).

Requiere en settings.py (variables de entorno):
  VAPID_PUBLIC_KEY   → clave pública VAPID en base64url sin padding
  VAPID_PRIVATE_KEY  → clave privada VAPID en formato PEM o base64url
  VAPID_ADMIN_EMAIL  → email de contacto (ej: admin@municipio.gob.ar)

Generar claves VAPID la primera vez:
  python -c "
  from py_vapid import Vapid
  v = Vapid()
  v.generate_keys()
  print('Private (PEM):', v.private_pem().decode())
  print('Public (base64url):', v.public_key)
  "

Endpoints:
  POST /push/suscribir/             → guarda o actualiza SuscripcionPush del conductor
  POST /push/acuse-anulacion/<id>/  → marca que el conductor se notificó de la anulación
  GET  /push/vapid-public-key/      → devuelve la clave pública para que el frontend suscriba

Acceso:
  suscribir          → @login_required (solo conductores autenticados)
  acuse-anulacion    → público (el conductor puede llegar desde el QR del acta)
  vapid-public-key   → público
"""

import json
import logging

from django.conf import settings
from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST, require_GET
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404

from .models import SuscripcionPush, Infraccion

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# Helpers internos
# ─────────────────────────────────────────────────────────────────────────────

def _get_ip(request):
    """Extrae la IP real del request (respeta X-Forwarded-For de Railway/proxies)."""
    x_forwarded = request.META.get("HTTP_X_FORWARDED_FOR")
    if x_forwarded:
        return x_forwarded.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR", "")


def enviar_push(suscripcion: SuscripcionPush, titulo: str, cuerpo: str, url: str = "/") -> bool:
    """
    Envía una notificación push a un dispositivo.
    Devuelve True si se envió correctamente, False si falló.
    Si el endpoint expiró (410 Gone), elimina la suscripción automáticamente.
    """
    try:
        from pywebpush import webpush, WebPushException
    except ImportError:
        logger.error("pywebpush no está instalado. Corré: pip install pywebpush")
        return False

    vapid_private_key = getattr(settings, "VAPID_PRIVATE_KEY", "")
    vapid_email       = getattr(settings, "VAPID_ADMIN_EMAIL", "admin@municipio.gob.ar")

    if not vapid_private_key:
        logger.warning("VAPID_PRIVATE_KEY no configurada — push desactivado")
        return False

    payload = json.dumps({"title": titulo, "body": cuerpo, "url": url}, ensure_ascii=False)

    try:
        webpush(
            subscription_info={
                "endpoint": suscripcion.endpoint,
                "keys": {
                    "p256dh": suscripcion.p256dh,
                    "auth":   suscripcion.auth,
                },
            },
            data=payload,
            vapid_private_key=vapid_private_key,
            vapid_claims={"sub": f"mailto:{vapid_email}"},
        )
        return True

    except Exception as exc:
        # 410 Gone: el browser revocó la suscripción → limpiar de la BD
        error_str = str(exc)
        if "410" in error_str or "Gone" in error_str:
            logger.info("Suscripción push vencida (410), eliminando: %s", suscripcion.id)
            suscripcion.delete()
        else:
            logger.warning("Error enviando push a %s: %s", suscripcion.endpoint[:40], exc)
        return False


# ─────────────────────────────────────────────────────────────────────────────
# Clave pública VAPID (para el frontend al suscribirse)
# ─────────────────────────────────────────────────────────────────────────────

@require_GET
def vapid_public_key(request):
    """
    GET /push/vapid-public-key/
    El frontend necesita esta clave antes de llamar a pushManager.subscribe().
    """
    clave = getattr(settings, "VAPID_PUBLIC_KEY", "")
    return JsonResponse({"publicKey": clave})


# ─────────────────────────────────────────────────────────────────────────────
# Registrar suscripción push
# ─────────────────────────────────────────────────────────────────────────────

@csrf_exempt
@login_required
@require_POST
def suscribir_push(request):
    """
    POST /push/suscribir/
    Body JSON: { endpoint, keys: { p256dh, auth } }

    Crea o actualiza la SuscripcionPush del conductor para este dispositivo.
    Si el endpoint ya existe pero pertenece a otro usuario, lo reasigna.
    """
    try:
        datos = json.loads(request.body)
        endpoint = datos.get("endpoint", "").strip()
        keys     = datos.get("keys", {})
        p256dh   = keys.get("p256dh", "").strip()
        auth     = keys.get("auth", "").strip()
    except (json.JSONDecodeError, AttributeError):
        return JsonResponse({"error": "JSON inválido"}, status=400)

    if not endpoint or not p256dh or not auth:
        return JsonResponse({"error": "Faltan datos de suscripción"}, status=400)

    # update_or_create por endpoint: si el mismo dispositivo se re-suscribe
    # con las mismas o nuevas claves, actualizamos sin duplicar.
    SuscripcionPush.objects.update_or_create(
        endpoint=endpoint,
        defaults={
            "usuario": request.user,
            "p256dh":  p256dh,
            "auth":    auth,
        },
    )

    return JsonResponse({"ok": True})


# ─────────────────────────────────────────────────────────────────────────────
# Acuse de recibo de anulación de infracción
# ─────────────────────────────────────────────────────────────────────────────

@csrf_exempt
@require_POST
def acuse_anulacion(request, infraccion_id):
    """
    POST /push/acuse-anulacion/<infraccion_id>/

    El conductor confirma desde la vista pública (/pagar/ o QR del acta) que
    se notificó de que su infracción fue anulada.

    Registra:
      - notificado_anulacion_en: timestamp exacto del acuse
      - notificado_anulacion_ip: IP del dispositivo del conductor

    Es idempotente: si ya estaba registrado, devuelve 200 sin pisar el dato.
    Acceso público (sin login) porque el conductor puede llegar desde el QR
    del acta impresa sin tener sesión activa.
    """
    infraccion = get_object_or_404(Infraccion, pk=infraccion_id, estado="anulada")

    # Idempotente: si ya se registró el acuse, no pisar el timestamp original
    if infraccion.notificado_anulacion_en:
        return JsonResponse({"ok": True, "ya_registrado": True})

    infraccion.notificado_anulacion_en = timezone.now()
    infraccion.notificado_anulacion_ip = _get_ip(request)
    infraccion.save(update_fields=["notificado_anulacion_en", "notificado_anulacion_ip"])

    return JsonResponse({"ok": True, "ya_registrado": False})

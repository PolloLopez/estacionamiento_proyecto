"""
Servicio centralizado de notificaciones.

Por qué existe este módulo:
- Antes, cada `Notificacion.objects.create(...)` estaba disperso en las vistas,
  sin tipo ni chequeo de preferencias del conductor.
- Centralizar el envío permite: respetar preferencias, añadir tipo, y en el futuro
  agregar canales adicionales (push, email) sin tocar cada vista.

Uso:
    from app_estacionamiento.services.notificaciones import enviar_notificacion
    enviar_notificacion(
        destinatario=usuario,
        mensaje="✅ Tu identidad fue verificada.",
        tipo="verificacion",
    )
"""

from ..models import Notificacion


# Mapa tipo → nombre del flag de preferencia en Usuario
_FLAG_POR_TIPO = {
    "verificacion": "notif_verificacion",
    "exencion":     "notif_exencion",
    "sugerencia":   "notif_sugerencia",
}


def enviar_notificacion(destinatario, mensaje, tipo=""):
    """
    Crea una Notificacion solo si el conductor no desactivó ese tipo.

    - Si tipo == "" (sin clasificar), siempre se envía.
    - Si el usuario desactivó el tipo, se omite silenciosamente (no lanza error).
    - Devuelve la instancia creada, o None si fue suprimida por preferencias.
    """
    if tipo:
        flag = _FLAG_POR_TIPO.get(tipo)
        if flag and not getattr(destinatario, flag, True):
            # El conductor desactivó este tipo de notificación
            return None

    return Notificacion.objects.create(
        destinatario=destinatario,
        mensaje=mensaje,
        tipo=tipo,
    )

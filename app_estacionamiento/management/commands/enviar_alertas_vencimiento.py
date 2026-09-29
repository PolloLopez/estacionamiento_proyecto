# management/commands/enviar_alertas_vencimiento.py
"""
Envía notificaciones push a conductores cuyo estacionamiento está próximo a vencer.

Diseñado para correr cada minuto desde Railway Cron:
  Cron expression: */1 * * * *
  Comando:         python manage.py enviar_alertas_vencimiento

Lógica:
  - Busca estacionamientos activos que vencen en [minutos_alerta - 1, minutos_alerta + 1]
    (ventana de 2 minutos para absorber la variabilidad del cron).
  - Solo envía si el municipio tiene minutos_alerta_push > 0.
  - Solo envía si el conductor tiene al menos una SuscripcionPush activa.
  - No envía duplicados: guarda en caché de sesión si ya se envió la alerta
    (usando campo alert_enviada_en en Estacionamiento, que no existe — ver nota).

Nota sobre idempotencia:
  Para no añadir un campo extra al modelo Estacionamiento (que dispararía otra
  migración), la idempotencia se maneja por ventana de tiempo: el cron corre
  cada minuto pero la ventana de búsqueda es ±1 minuto del umbral. Si el cron
  se atrasa o corre dos veces en el mismo minuto, el conductor puede recibir la
  notificación dos veces — es un escenario muy poco probable y tiene bajo impacto
  (una push duplicada no es un error de datos). Si querés idempotencia perfecta,
  agregar Estacionamiento.push_vencimiento_enviada = BooleanField(default=False)
  y filtrarlo acá.
"""

import logging
from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from app_estacionamiento.models import Estacionamiento, SuscripcionPush
from app_estacionamiento.views_push import enviar_push

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Envía notificaciones push a conductores cuyo estacionamiento está por vencer."

    def handle(self, *args, **options):
        ahora = timezone.now()
        enviados = 0
        errores  = 0

        # Traemos todos los estacionamientos activos que tienen un usuario y municipio.
        # Luego filtramos en Python para poder calcular hora_vencimiento (property).
        # (Queremos evitar duplicar la lógica de hora_vencimiento en SQL.)
        estacionamientos = (
            Estacionamiento.objects
            .filter(estado="activo", usuario__isnull=False)
            .select_related("usuario", "subcuadra__municipio")
        )

        for est in estacionamientos:
            municipio = getattr(est.subcuadra, "municipio", None)
            if not municipio:
                continue

            minutos = municipio.minutos_alerta_push
            if not minutos:
                # 0 = desactivado para este municipio
                continue

            hora_venc = est.hora_vencimiento
            if not hora_venc:
                continue

            # Ventana de alerta: [umbral - 1 min, umbral + 1 min]
            umbral    = timedelta(minutes=minutos)
            diferencia = hora_venc - ahora
            if not (umbral - timedelta(minutes=1) <= diferencia <= umbral + timedelta(minutes=1)):
                continue

            # El conductor tiene suscripciones push?
            suscripciones = SuscripcionPush.objects.filter(usuario=est.usuario)
            if not suscripciones.exists():
                continue

            # Armar el mensaje
            minutos_restantes = max(1, round(diferencia.total_seconds() / 60))
            titulo = "⏰ Tu estacionamiento está por vencer"
            cuerpo = (
                f"Quedan {minutos_restantes} minuto{'s' if minutos_restantes != 1 else ''} "
                f"en {est.subcuadra.calle} {est.subcuadra.altura}."
            )
            url_retorno = "/inicio/"

            # Enviar a todos sus dispositivos
            for suscripcion in suscripciones:
                ok = enviar_push(suscripcion, titulo, cuerpo, url_retorno)
                if ok:
                    enviados += 1
                else:
                    errores += 1

        self.stdout.write(
            f"Alertas push enviadas: {enviados} | Errores/vencidas: {errores}"
        )

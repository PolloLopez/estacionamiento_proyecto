# app_estacionamiento/use_cases/pagar_infraccion.py
from datetime import timedelta

from django.db import transaction
from django.utils import timezone

from app_estacionamiento.models import Infraccion, Usuario

from app_estacionamiento.use_cases.registrar_movimiento import (
    ejecutar as registrar_movimiento
)


def ejecutar(usuario, infraccion):
    """
    Paga una infracción del conductor con su saldo.

    Tolerancia de gracia: si el conductor paga dentro de los primeros
    X minutos (configurado en municipio.tolerancia_multa_minutos, default 5),
    la infracción se ANULA automáticamente sin cobrar nada.

    Retorna la infracción actualizada. Incluye el campo:
      - infraccion.anulada_por_gracia (True si se anuló, False si se cobró)

    Usa select_for_update() para evitar race conditions de doble pago.
    """
    with transaction.atomic():
        # Bloquear filas para prevenir doble pago concurrente
        infraccion_locked = Infraccion.objects.select_for_update().get(pk=infraccion.pk)
        usuario_locked    = Usuario.objects.select_for_update().get(pk=usuario.pk)

        if infraccion_locked.estado != "pendiente":
            raise Exception("La infracción ya fue procesada")

        # ── Tolerancia de gracia ─────────────────────────────────────────────
        # Si el municipio tiene tolerancia configurada y el conductor paga
        # dentro de ese plazo, la multa se cancela automáticamente sin cobro.
        tolerancia_min = 0
        if infraccion_locked.municipio:
            tolerancia_min = infraccion_locked.municipio.tolerancia_multa_minutos or 0

        ahora = timezone.now()
        tiempo_transcurrido = ahora - infraccion_locked.creado_en

        if tolerancia_min > 0 and tiempo_transcurrido <= timedelta(minutes=tolerancia_min):
            # Cancelar sin cobrar
            infraccion_locked.estado = "anulada"
            infraccion_locked.fecha_pago = ahora
            infraccion_locked.save()
            infraccion_locked.anulada_por_gracia = True
            return infraccion_locked

        # ── Cobro normal ─────────────────────────────────────────────────────
        if usuario_locked.saldo < infraccion_locked.monto:
            raise Exception("Saldo insuficiente")

        usuario_locked.saldo -= infraccion_locked.monto
        usuario_locked.save()

        infraccion_locked.estado = "pagada"
        infraccion_locked.fecha_pago = ahora
        infraccion_locked.save()

        registrar_movimiento(
            usuario=usuario_locked,
            monto=infraccion_locked.monto,
            tipo="egreso",
            descripcion=f"Pago infracción #{infraccion_locked.id} — {infraccion_locked.vehiculo.patente}",
        )

    infraccion_locked.anulada_por_gracia = False
    return infraccion_locked

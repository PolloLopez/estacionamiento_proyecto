# app_estacionamiento/use_cases/pagar_infraccion.py
from django.db import transaction
from django.utils import timezone

from app_estacionamiento.models import Infraccion, Usuario

from app_estacionamiento.use_cases.registrar_movimiento import (
    ejecutar as registrar_movimiento
)


def ejecutar(usuario, infraccion):
    """
    Descuenta el monto de la infraccion del saldo del conductor y la marca como pagada.

    Usa select_for_update() en ambas filas para evitar race conditions:
    si dos requests llegan al mismo tiempo, el segundo espera al primero
    y luego falla por estado != pendiente o saldo insuficiente.
    """
    with transaction.atomic():
        # Bloquear filas para prevenir doble pago concurrente
        infraccion_locked = Infraccion.objects.select_for_update().get(pk=infraccion.pk)
        usuario_locked = Usuario.objects.select_for_update().get(pk=usuario.pk)

        if infraccion_locked.estado != "pendiente":
            raise Exception("La infraccion ya fue procesada")

        if usuario_locked.saldo < infraccion_locked.monto:
            raise Exception("Saldo insuficiente")

        usuario_locked.saldo -= infraccion_locked.monto
        usuario_locked.save()

        infraccion_locked.estado = "pagada"
        infraccion_locked.fecha_pago = timezone.now()
        infraccion_locked.save()

        registrar_movimiento(
            usuario=usuario_locked,
            monto=infraccion_locked.monto,
            tipo="egreso",
            descripcion=f"Infraccion #{infraccion_locked.id}"
        )

    return infraccion_locked

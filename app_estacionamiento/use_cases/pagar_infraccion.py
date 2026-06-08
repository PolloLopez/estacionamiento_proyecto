# app_estacionamiento/use_cases/pagar_infraccion.py
from django.db import transaction
from django.utils import timezone

from app_estacionamiento.models import Infraccion

from app_estacionamiento.use_cases.registrar_movimiento import (
    ejecutar as registrar_movimiento
)


def ejecutar(usuario, infraccion):

    with transaction.atomic():

        if infraccion.estado != "pendiente":
            raise Exception(
                "La infracción ya fue procesada"
            )

        if usuario.saldo < infraccion.monto:
            raise Exception(
                "Saldo insuficiente"
            )

        usuario.saldo -= infraccion.monto
        usuario.save()

        infraccion.estado = "pagada"
        infraccion.fecha_pago = timezone.now()
        infraccion.save()

        registrar_movimiento(
            usuario=usuario,
            monto=infraccion.monto,
            tipo="egreso",
            descripcion=f"Infracción #{infraccion.id}"
        )

    return infraccion
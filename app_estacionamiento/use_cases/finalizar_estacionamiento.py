# app_estacionamiento/use_cases/finalizar_estacionamiento.py

from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from app_estacionamiento.models import (
    Estacionamiento,
    Usuario,
    Estado
)

TARIFA_MINIMA = Decimal("100")


def ejecutar(estacionamiento):

    with transaction.atomic():

        estacionamiento = (
            Estacionamiento.objects
            .select_for_update()
            .get(id=estacionamiento.id)
        )

        if estacionamiento.estado != Estado.ACTIVO:
            return {
                "ok": False,
                "error": "Ya finalizado"
            }

        estacionamiento.hora_fin = timezone.now()
        estacionamiento.estado = Estado.FINALIZADO

        costo = estacionamiento.costo_base

        if not costo:
            costo = TARIFA_MINIMA

        estacionamiento.costo_final = costo

        estacionamiento.save()

        return {
            "ok": True,
            "costo": costo
        }
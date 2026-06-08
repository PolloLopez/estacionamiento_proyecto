# app_estacionamiento/use_cases/registrar_infraccion.py
from django.db import transaction

from app_estacionamiento.models import (
    Infraccion
)


def ejecutar(
    vehiculo,
    inspector,
    subcuadra,
    motivo,
    monto,
    foto=None
):

    with transaction.atomic():

        infraccion = Infraccion.objects.create(
            vehiculo=vehiculo,
            inspector=inspector,
            subcuadra=subcuadra,
            motivo=motivo,
            monto=monto,
            foto=foto,
            estado="pendiente"
        )

    return infraccion
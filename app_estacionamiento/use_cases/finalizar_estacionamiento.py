# app_estacionamiento/use_cases/finalizar_estacionamiento.py
"""
Finaliza un estacionamiento activo anticipadamente.

El saldo ya fue debitado al INICIAR el estacionamiento.
Este use case solo cambia el estado a FINALIZADO y registra la hora de cierre.
No hay devolución de saldo al finalizar: si el municipio tiene módulo de reintegro,
ese crédito ya se aplicó al inicio (services/reintegro.py via estacionar_vehiculo.py).
"""

from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from app_estacionamiento.models import (
    Estacionamiento,
    Estado,
)


def ejecutar(estacionamiento):
    """
    Finaliza un estacionamiento activo.

    Retorna dict con:
      ok                    (bool)
      costo                 (Decimal)  costo_base del estacionamiento
      minutos_transcurridos (int)
    """

    with transaction.atomic():

        estacionamiento = (
            Estacionamiento.objects
            .select_for_update()
            .get(id=estacionamiento.id)
        )

        if estacionamiento.estado != Estado.ACTIVO:
            return {
                "ok":                    False,
                "error":                 "Ya finalizado",
                "minutos_transcurridos": 0,
            }

        ahora = timezone.now()
        estacionamiento.hora_fin  = ahora
        estacionamiento.estado    = Estado.FINALIZADO
        # El costo_final es el mismo que el costo_base: ya fue cobrado al inicio.
        estacionamiento.costo_final = estacionamiento.costo_base or Decimal("0")
        estacionamiento.save()

        minutos_transcurridos = int((ahora - estacionamiento.hora_inicio).total_seconds() / 60)

        return {
            "ok":                    True,
            "costo":                 estacionamiento.costo_final,
            "minutos_transcurridos": minutos_transcurridos,
        }

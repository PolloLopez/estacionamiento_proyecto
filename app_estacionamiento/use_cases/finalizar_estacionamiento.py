# app_estacionamiento/use_cases/finalizar_estacionamiento.py

from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from app_estacionamiento.models import (
    Estacionamiento,
    MovimientoCaja,
    Usuario,
    Estado,
)

TARIFA_MINIMA = Decimal("100")

# Si el conductor finaliza antes de este umbral, se le devuelve el 100% del costo.
UMBRAL_REINTEGRO_MINUTOS = 30


def ejecutar(estacionamiento):
    """
    Finaliza un estacionamiento activo.

    Regla de reintegro:
      Si el tiempo transcurrido desde el inicio es menor a UMBRAL_REINTEGRO_MINUTOS,
      se devuelve el 100% del costo_base al saldo del conductor y costo_final queda en 0.
      Caso contrario, costo_final = costo_base.

    Retorna dict con:
      ok                    (bool)
      costo                 (Decimal)  costo_final cobrado
      reintegro             (bool)     True si hubo devolucion de saldo
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
                "reintegro":             False,
                "minutos_transcurridos": 0,
            }

        ahora = timezone.now()
        estacionamiento.hora_fin = ahora
        estacionamiento.estado   = Estado.FINALIZADO

        costo = estacionamiento.costo_base or TARIFA_MINIMA

        # Chequeo de reintegro: si finalizo antes del umbral, devolver saldo completo.
        # Lock sobre el conductor para evitar race conditions con otros debitos simultaneos.
        minutos_transcurridos = int((ahora - estacionamiento.hora_inicio).total_seconds() / 60)
        reintegro = minutos_transcurridos < UMBRAL_REINTEGRO_MINUTOS

        if reintegro:
            conductor = (
                Usuario.objects
                .select_for_update()
                .get(id=estacionamiento.usuario_id)
            )
            conductor.saldo += costo
            conductor.save(update_fields=["saldo"])

            MovimientoCaja.objects.create(
                usuario=conductor,
                monto=costo,
                tipo="ingreso",
                descripcion=(
                    f"Reintegro: estacionamiento finalizado a los "
                    f"{minutos_transcurridos} min (< {UMBRAL_REINTEGRO_MINUTOS} min)"
                ),
            )
            costo_final = Decimal("0")
        else:
            costo_final = costo

        estacionamiento.costo_final = costo_final
        estacionamiento.save()

        return {
            "ok":                    True,
            "costo":                 costo_final,
            "reintegro":             reintegro,
            "minutos_transcurridos": minutos_transcurridos,
        }

# app_estacionamiento/use_cases/cobrar_estacionamiento.py
from decimal import Decimal
from django.db import transaction

from app_estacionamiento.models import Usuario, MovimientoCaja


def ejecutar(inspector, monto, descripcion=""):

    monto = Decimal(monto)

    with transaction.atomic():

        inspector = Usuario.objects.select_for_update().get(id=inspector.id)

        # 💰 SUMA al saldo operativo del inspector
        inspector.saldo_operativo += monto
        inspector.save()

        movimiento = MovimientoCaja.objects.create(
            usuario=inspector,
            monto=monto,
            tipo="ingreso",
            descripcion=descripcion
        )

    return {
        "ok": True,
        "movimiento": movimiento
    }
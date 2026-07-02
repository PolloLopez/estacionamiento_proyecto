# app_estacionamiento/use_cases/cobrar_estacionamiento.py
from decimal import Decimal
from django.db import transaction

from app_estacionamiento.models import Usuario, MovimientoCaja


def ejecutar(inspector, monto, descripcion="", comision_monto=Decimal("0")):
    """
    Registra un cobro en la caja del inspector o vendedor.

    comision_monto: porcion del monto que corresponde al usuario (calculada en la vista).
    """
    monto = Decimal(monto)
    comision_monto = Decimal(comision_monto)

    with transaction.atomic():
        inspector = Usuario.objects.select_for_update().get(id=inspector.id)

        # Suma al saldo operativo
        inspector.saldo_operativo += monto
        inspector.save()

        movimiento = MovimientoCaja.objects.create(
            usuario=inspector,
            monto=monto,
            tipo="ingreso",
            medio_pago="efectivo",
            comision_monto=comision_monto,
            descripcion=descripcion,
        )

    return {
        "ok": True,
        "movimiento": movimiento,
    }

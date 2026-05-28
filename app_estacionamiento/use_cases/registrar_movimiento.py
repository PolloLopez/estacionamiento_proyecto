from decimal import Decimal
from django.db import transaction

from app_estacionamiento.models import Usuario, MovimientoCaja


def ejecutar(usuario, monto, tipo, descripcion=""):

    monto = Decimal(monto)

    with transaction.atomic():

        usuario = Usuario.objects.select_for_update().get(id=usuario.id)

        # ============================
        # REGLA: egreso no puede dejar saldo negativo
        # ============================
        if tipo == "egreso":
            if usuario.saldo_operativo < monto:
                return {
                    "ok": False,
                    "error": "Saldo operativo insuficiente"
                }

            usuario.saldo_operativo -= monto

        elif tipo == "ingreso":
            usuario.saldo_operativo += monto

        usuario.save()

        movimiento = MovimientoCaja.objects.create(
            usuario=usuario,
            monto=monto,
            tipo=tipo,
            descripcion=descripcion
        )

    return {
        "ok": True,
        "movimiento": movimiento
    }
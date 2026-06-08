# app_estacionamiento/use_cases/registrar_movimiento.py

from decimal import Decimal
from django.db import transaction

from app_estacionamiento.models import Usuario, MovimientoCaja


def ejecutar(usuario, monto, tipo, descripcion=""):

    monto = Decimal(monto)

    with transaction.atomic():

        return MovimientoCaja.objects.create(
            usuario=usuario,
            monto=monto,
            tipo=tipo,
            descripcion=descripcion
        )
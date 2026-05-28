
# app_estacionamiento/services_caja.py
from decimal import Decimal
from django.utils import timezone
from django.db.models import Sum
from django.db import transaction
from app_estacionamiento.models import MovimientoCaja, CierreCaja, Usuario

def cobrar_estacionamiento(inspector, monto, descripcion=""):

    monto = Decimal(monto)

    with transaction.atomic():

        inspector = Usuario.objects.select_for_update().get(id=inspector.id)

        if inspector.saldo_operativo < monto:
            raise Exception("Saldo insuficiente")

        # ✅ DESCUENTA saldo operativo (correcto para inspector)
        inspector.saldo_operativo -= monto
        inspector.save()

        MovimientoCaja.objects.create(
            usuario=inspector,
            monto=monto,
            tipo="ingreso",  # plata que entra desde la calle
            descripcion=descripcion
        )

def generar_cierre_caja(usuario):

    movimientos = MovimientoCaja.objects.filter(
        usuario=usuario,
        tipo="ingreso",
        cerrado=False  # 🔥 CLAVE
    )

    total = movimientos.aggregate(
        total=Sum("monto")
    )["total"] or Decimal("0")

    cierre = CierreCaja.objects.create(
        usuario=usuario,
        total_cobrado=total,
        fecha=timezone.now()
    )

    # 🔒 marcar como cerrados
    movimientos.update(cerrado=True)

    return cierre
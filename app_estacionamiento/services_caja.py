
# app_estacionamiento/services_caja.py
from decimal import Decimal
from django.utils import timezone
from django.db.models import Sum
from django.db import transaction
from app_estacionamiento.models import MovimientoCaja, CierreCaja, Usuario

def cobrar_estacionamiento(inspector, monto, descripcion=""):

    monto = Decimal(monto)

    return MovimientoCaja.objects.create(
        usuario=inspector,
        monto=monto,
        tipo="ingreso",       # 🔥 CLAVE
        descripcion=descripcion,
        cerrado=False         # 🔥 CLAVE
    )

def generar_cierre_caja(usuario):

    movimientos = MovimientoCaja.objects.filter(
        usuario=usuario,
        tipo="ingreso",
        cerrado=False
    ).order_by("fecha")

    if not movimientos.exists():
        return None

    total = movimientos.aggregate(
        total=Sum("monto")
    )["total"] or Decimal("0")

    fecha_apertura = movimientos.first().fecha

    cierre = CierreCaja.objects.create(
        usuario=usuario,
        total_cobrado=total,
        fecha_apertura=fecha_apertura,
        cantidad_movimientos=movimientos.count()
    )

    movimientos.update(cerrado=True)

    return cierre
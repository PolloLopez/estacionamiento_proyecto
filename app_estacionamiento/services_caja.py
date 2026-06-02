
# app_estacionamiento/services_caja.py
from django.db.models import Sum
from decimal import Decimal
from django.utils import timezone
from app_estacionamiento.models import MovimientoCaja, CierreCaja

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
    fecha_cierre = timezone.now()

    cierre = CierreCaja.objects.create(
        usuario=usuario,
        total_cobrado=total,
        fecha_apertura=movimientos.first().fecha,
        cantidad_movimientos=movimientos.count(),
        creado_en=timezone.now()
    )

    # 🔒 corte real (auditoría)
    movimientos.update(cerrado=True)

    return cierre
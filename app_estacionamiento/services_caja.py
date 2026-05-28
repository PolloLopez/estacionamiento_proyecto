from decimal import Decimal
from django.db.models import Sum

from app_estacionamiento.models import MovimientoCaja, CierreCaja


def generar_cierre_caja(usuario):

    total = MovimientoCaja.objects.filter(
        usuario=usuario
    ).aggregate(total=Sum("monto"))["total"] or Decimal("0")

    cierre = CierreCaja.objects.create(
        usuario=usuario,
        total_cobrado=total
    )

    MovimientoCaja.objects.filter(
        usuario=usuario
    ).update(descripcion="CIERRE_CAJERO")

    return cierre
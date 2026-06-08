# app_estacionamiento/services_caja.py
from django.db.models import Sum
from decimal import Decimal
from django.utils import timezone
from app_estacionamiento.models import MovimientoCaja, CierreCaja
from django.db import transaction

def generar_cierre_caja(usuario, fecha_desde=None, fecha_hasta=None):

    with transaction.atomic():

        movimientos = MovimientoCaja.objects.select_for_update().filter(
            usuario=usuario,
            tipo="ingreso",
            cerrado=False
        ).order_by("creado_en")

        # 📅 filtro por período (opcional)
        if fecha_desde:
            movimientos = movimientos.filter(creado_en__gte=fecha_desde)

        if fecha_hasta:
            movimientos = movimientos.filter(creado_en__lte=fecha_hasta)

        if not movimientos.exists():
            return None

        total = movimientos.aggregate(
            total=Sum("monto")
        )["total"] or Decimal("0")

        fecha_apertura = movimientos.first().creado_en

        cierre = CierreCaja.objects.create(
            usuario=usuario,
            total_cobrado=total,
            fecha_apertura=fecha_apertura,
            cantidad_movimientos=movimientos.count(),
            creado_por=usuario
        )

        # 🔒 BLOQUEO DEFINITIVO (clave contable)
        movimientos.update(cerrado=True)

        return cierre
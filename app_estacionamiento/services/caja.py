# app_estacionamiento/services/caja.py
"""
Lógica de negocio relacionada con cierres de caja y movimientos.

Responsabilidades:
- Generar el cierre de caja de un inspector/vendedor (con comisión)
"""

from decimal import Decimal, ROUND_HALF_UP

from django.db import transaction
from django.db.models import Sum
from django.utils import timezone

from app_estacionamiento.models import CierreCaja, MovimientoCaja


def generar_cierre_caja(usuario, fecha_desde=None, fecha_hasta=None, periodo=""):
    """
    Genera un CierreCaja atómico para el usuario (inspector o vendedor).

    - Cierra todos los MovimientoCaja de tipo 'ingreso' que estén abiertos.
    - Aplica el porcentaje_ganancia del usuario para calcular
      ganancia_usuario y monto_municipio.
    - Retorna el CierreCaja creado, o None si no había movimientos.
    """
    with transaction.atomic():
        movimientos = MovimientoCaja.objects.select_for_update().filter(
            usuario=usuario,
            tipo="ingreso",
            cerrado=False,
        ).order_by("creado_en")

        if fecha_desde:
            movimientos = movimientos.filter(creado_en__gte=fecha_desde)
        if fecha_hasta:
            movimientos = movimientos.filter(creado_en__lte=fecha_hasta)

        if not movimientos.exists():
            return None

        total          = movimientos.aggregate(total=Sum("monto"))["total"] or Decimal("0")
        fecha_apertura = movimientos.first().creado_en

        # Comisión: snapshot del porcentaje actual al momento del cierre
        porcentaje = usuario.porcentaje_ganancia or Decimal("0")
        ganancia   = (total * porcentaje / Decimal("100")).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )
        monto_municipio = total - ganancia

        cierre = CierreCaja.objects.create(
            usuario=usuario,
            total_cobrado=total,
            fecha_apertura=fecha_apertura,
            cantidad_movimientos=movimientos.count(),
            creado_por=usuario,
            periodo=periodo,
            porcentaje_ganancia_aplicado=porcentaje,
            ganancia_usuario=ganancia,
            monto_municipio=monto_municipio,
        )

        # Bloqueo definitivo: una vez cerrado no se puede reabrir
        movimientos.update(cerrado=True)

        return cierre

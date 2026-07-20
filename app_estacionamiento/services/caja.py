# app_estacionamiento/services/caja.py
"""
Lógica de negocio relacionada con cierres de caja y movimientos.

Responsabilidades:
- Registrar un cobro efectivo en la caja del cobrador (vendedor/admin)
- Generar el cierre de caja de un inspector/vendedor (con comisión)
"""

from decimal import Decimal, ROUND_HALF_UP

from django.db import transaction
from django.db.models import Sum
from django.utils import timezone

from app_estacionamiento.models import CierreCaja, MovimientoCaja


def registrar_cobro_efectivo(cobrador, monto: Decimal, descripcion: str = "", comision_monto: Decimal = Decimal("0")):
    """
    Registra un cobro en efectivo del cobrador (vendedor o admin).

    - Suma el monto al saldo_operativo del cobrador (select_for_update).
    - Crea el MovimientoCaja de tipo 'ingreso' con su comisión.

    Parámetros:
        cobrador:       instancia de Usuario (vendedor o admin)
        monto:          Decimal, total cobrado
        descripcion:    texto libre para el MovimientoCaja
        comision_monto: Decimal, porción que retiene el cobrador

    Retorna:
        El MovimientoCaja creado.
    """
    from app_estacionamiento.models import Usuario

    with transaction.atomic():
        cobrador_locked = Usuario.objects.select_for_update().get(id=cobrador.id)
        cobrador_locked.saldo_operativo += monto
        cobrador_locked.save(update_fields=["saldo_operativo"])
        return MovimientoCaja.objects.create(
            usuario=cobrador_locked,
            monto=monto,
            tipo="ingreso",
            medio_pago="efectivo",
            comision_monto=comision_monto,
            descripcion=descripcion,
        )


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

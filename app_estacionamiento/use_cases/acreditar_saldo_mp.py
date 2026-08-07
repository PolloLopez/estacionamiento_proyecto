"""
Use case: acreditar saldo al conductor después de un pago exitoso en MercadoPago.

Recibe el payment_id de MP, verifica el estado del pago consultando la API,
y si está aprobado acredita el monto al usuario y registra el movimiento de caja.

Se llama desde la vista del webhook (mp_webhook) y también desde la vista
de retorno exitoso (mp_exitoso) como fallback.
"""

from decimal import Decimal
from django.db import transaction
from app_estacionamiento.models import Usuario, MovimientoCaja


def ejecutar(usuario: Usuario, monto: Decimal, payment_id: str) -> None:
    """
    Acredita `monto` al saldo del usuario y registra el movimiento.

    Args:
        usuario:    El conductor que realizó el pago.
        monto:      Monto en pesos a acreditar.
        payment_id: ID del pago en MercadoPago (para trazabilidad).

    Raises:
        ValueError: Si el monto es inválido.
        Exception:  Si el usuario ya fue acreditado por este payment_id.
    """
    if monto <= 0:
        raise ValueError(f"Monto inválido: {monto}")

    # Idempotencia: el webhook de MP puede llegar más de una vez para el mismo pago.
    # Chequeamos por mp_payment_id (campo unique) en lugar de buscar en el texto
    # de descripción, que era frágil ante cualquier cambio de formato.
    ya_acreditado = MovimientoCaja.objects.filter(mp_payment_id=payment_id).exists()

    if ya_acreditado:
        return

    with transaction.atomic():
        usuario_locked = Usuario.objects.select_for_update().get(pk=usuario.pk)
        usuario_locked.saldo += monto
        usuario_locked.save()

        MovimientoCaja.objects.create(
            usuario=usuario_locked,
            monto=monto,
            tipo="ingreso",
            medio_pago="mercadopago",
            mp_payment_id=payment_id,
            descripcion=f"Carga de saldo via MercadoPago",
        )

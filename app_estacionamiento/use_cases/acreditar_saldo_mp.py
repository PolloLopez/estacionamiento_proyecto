"""
Use case: acreditar saldo al conductor después de un pago exitoso en MercadoPago.

Recibe el payment_id de MP, verifica el estado del pago consultando la API,
y si está aprobado acredita el monto al usuario en la billetera del municipio
correspondiente y registra el movimiento de caja.

Se llama desde la vista del webhook (mp_webhook) y también desde la vista
de retorno exitoso (mp_exitoso) como fallback.
"""

from decimal import Decimal
from django.db import transaction
from app_estacionamiento.models import Usuario, MovimientoCaja, BilleteraConductor


def ejecutar(usuario: Usuario, monto: Decimal, payment_id: str, municipio=None) -> None:
    """
    Acredita `monto` en la billetera del conductor (municipio dado) y registra el movimiento.

    Args:
        usuario:    El conductor que realizó el pago.
        monto:      Monto en pesos a acreditar.
        payment_id: ID del pago en MercadoPago (para trazabilidad).
        municipio:  Municipio donde acreditar. Si None, usa usuario.municipio.

    Raises:
        ValueError: Si el monto es inválido.
    """
    if monto <= 0:
        raise ValueError(f"Monto inválido: {monto}")

    municipio = municipio or usuario.municipio

    # Idempotencia: el webhook de MP puede llegar más de una vez para el mismo pago.
    # Chequeamos por mp_payment_id (campo unique) en lugar de buscar en el texto
    # de descripción, que era frágil ante cualquier cambio de formato.
    ya_acreditado = MovimientoCaja.objects.filter(mp_payment_id=payment_id).exists()

    if ya_acreditado:
        return

    with transaction.atomic():
        if municipio is not None:
            # Acreditar en la billetera del municipio
            billetera, _ = BilleteraConductor.objects.select_for_update().get_or_create(
                conductor=usuario,
                municipio=municipio,
                defaults={"saldo": Decimal("0")},
            )
            billetera.saldo += monto
            billetera.save(update_fields=["saldo"])
        else:
            # Fallback legacy (sin municipio): debitar de usuario.saldo
            usuario_locked = Usuario.objects.select_for_update().get(pk=usuario.pk)
            usuario_locked.saldo += monto
            usuario_locked.save(update_fields=["saldo"])

        MovimientoCaja.objects.create(
            usuario=usuario,
            monto=monto,
            tipo="ingreso",
            medio_pago="mercadopago",
            mp_payment_id=payment_id,
            descripcion="Carga de saldo via MercadoPago",
        )

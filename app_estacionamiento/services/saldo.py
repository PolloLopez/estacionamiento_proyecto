# app_estacionamiento/services/saldo.py
"""
Lógica de negocio relacionada con el saldo de los conductores.

Responsabilidades:
- Carga manual de saldo por parte de un admin (con registro contable)

La acreditación automática vía MercadoPago vive en:
    use_cases/acreditar_saldo_mp.py
"""

from decimal import Decimal

from django.db import transaction

from app_estacionamiento.models import MovimientoCaja


def cargar_saldo_conductor(admin, conductor, monto: Decimal):
    """
    El admin carga saldo a un conductor manualmente (cobro en efectivo, corrección, etc.).

    Pasos:
    1. Suma el monto al saldo del conductor.
    2. Registra el ingreso en la caja del admin (para trazabilidad y rendición).

    Parámetros:
        admin: instancia de Usuario con rol admin (el que realiza la operación)
        conductor: instancia de Usuario con rol conductor (el que recibe el saldo)
        monto: Decimal positivo a acreditar

    Retorna:
        El conductor con el saldo actualizado.

    Lanza:
        ValueError si el monto es menor o igual a 0.
    """
    if monto <= 0:
        raise ValueError("El monto debe ser mayor a 0.")

    with transaction.atomic():
        conductor.saldo += monto
        conductor.save(update_fields=["saldo"])

        MovimientoCaja.objects.create(
            usuario=admin,
            monto=monto,
            tipo="ingreso",
            descripcion=(
                f"Carga de saldo para {conductor.correo} por {admin.correo}"
            ),
        )

    return conductor

def debitar_saldo_conductor(conductor, monto: Decimal, descripcion: str = ""):
    """
    Descuenta saldo al conductor y registra el egreso en caja.

    IMPORTANTE: debe llamarse desde dentro de un bloque transaction.atomic()
    con el conductor ya bloqueado con select_for_update(). No abre su propia
    transacción para no romper el lock del llamador.

    Parámetros:
        conductor: instancia de Usuario ya bloqueada (select_for_update)
        monto:     Decimal a descontar
        descripcion: texto para el MovimientoCaja

    Lanza:
        ValueError si el saldo es insuficiente.
    """
    if conductor.saldo < monto:
        raise ValueError(
            f"Saldo insuficiente. Disponible: {conductor.saldo}, requerido: {monto}."
        )
    conductor.saldo -= monto
    conductor.save(update_fields=["saldo"])
    MovimientoCaja.objects.create(
        usuario=conductor,
        monto=monto,
        tipo="egreso",
        descripcion=descripcion,
    )

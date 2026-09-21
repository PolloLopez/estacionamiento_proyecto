# app_estacionamiento/services/saldo.py
"""
Lógica de negocio relacionada con el saldo de los conductores.

Responsabilidades:
- Acceso a la billetera por municipio (BilleteraConductor)
- Carga manual de saldo por parte de un admin (con registro contable)
- Débito de saldo durante operaciones del conductor

La acreditación automática vía MercadoPago vive en:
    use_cases/acreditar_saldo_mp.py
"""

from decimal import Decimal

from django.db import transaction

from app_estacionamiento.models import BilleteraConductor, MovimientoCaja


# ──────────────────────────────────────────────────────────────────────────────
# Helpers de billetera
# ──────────────────────────────────────────────────────────────────────────────

def obtener_o_crear_billetera(conductor, municipio):
    """
    Devuelve la BilleteraConductor del conductor para el municipio dado.
    Si no existe, la crea con saldo 0.

    Nota: se llama FUERA de una transacción atómica (solo para leer el saldo
    o para contexto). Para operaciones de débito/crédito usar las funciones
    específicas que gestionan el lock.
    """
    billetera, _ = BilleteraConductor.objects.get_or_create(
        conductor=conductor,
        municipio=municipio,
        defaults={"saldo": Decimal("0")},
    )
    return billetera


def obtener_saldo_conductor(conductor, municipio):
    """
    Devuelve el saldo del conductor en el municipio dado.
    Si no tiene billetera, devuelve 0.
    """
    billetera = BilleteraConductor.objects.filter(
        conductor=conductor, municipio=municipio
    ).first()
    return billetera.saldo if billetera else Decimal("0")


# ──────────────────────────────────────────────────────────────────────────────
# Operaciones de crédito / débito
# ──────────────────────────────────────────────────────────────────────────────

def cargar_saldo_conductor(admin, conductor, monto: Decimal, municipio=None):
    """
    El admin carga saldo a un conductor manualmente (cobro en efectivo, corrección, etc.).

    Pasos:
    1. Acredita el monto en la BilleteraConductor del municipio correspondiente.
    2. Registra el ingreso en la caja del admin (para trazabilidad y rendición).

    Parámetros:
        admin:      instancia de Usuario con rol admin (el que realiza la operación)
        conductor:  instancia de Usuario con rol conductor (el que recibe el saldo)
        monto:      Decimal positivo a acreditar
        municipio:  Municipio donde se acredita. Si None, usa admin.municipio.

    Retorna:
        La BilleteraConductor actualizada.

    Lanza:
        ValueError si el monto es menor o igual a 0.
    """
    if monto <= 0:
        raise ValueError("El monto debe ser mayor a 0.")

    municipio = municipio or admin.municipio

    with transaction.atomic():
        billetera, _ = BilleteraConductor.objects.select_for_update().get_or_create(
            conductor=conductor,
            municipio=municipio,
            defaults={"saldo": Decimal("0")},
        )
        billetera.saldo += monto
        billetera.save(update_fields=["saldo"])

        MovimientoCaja.objects.create(
            usuario=admin,
            monto=monto,
            tipo="ingreso",
            descripcion=(
                f"Carga de saldo para {conductor.correo} por {admin.correo}"
            ),
        )

    return billetera


def debitar_saldo_conductor(
    conductor, monto: Decimal, descripcion: str = "", municipio=None
):
    """
    Descuenta saldo al conductor de su billetera en el municipio dado.

    IMPORTANTE: debe llamarse desde dentro de un bloque transaction.atomic()
    con el conductor ya bloqueado con select_for_update(). No abre su propia
    transacción para no romper el lock del llamador.

    Parámetros:
        conductor:   instancia de Usuario ya bloqueada (select_for_update)
        monto:       Decimal a descontar
        descripcion: texto para el MovimientoCaja
        municipio:   Municipio del que se debita. Si None, usa conductor.municipio.

    Lanza:
        ValueError si el saldo es insuficiente.
    """
    municipio = municipio or conductor.municipio

    if municipio is None:
        # Fallback legacy: sin municipio asociado, debitar de conductor.saldo
        # (solo puede ocurrir en entornos de test mal configurados)
        if conductor.saldo < monto:
            raise ValueError(
                f"Saldo insuficiente. Disponible: {conductor.saldo}, requerido: {monto}."
            )
        conductor.saldo -= monto
        conductor.save(update_fields=["saldo"])
    else:
        # Camino normal: billetera por municipio
        billetera, _ = BilleteraConductor.objects.select_for_update().get_or_create(
            conductor=conductor,
            municipio=municipio,
            defaults={"saldo": Decimal("0")},
        )
        if billetera.saldo < monto:
            raise ValueError(
                f"Saldo insuficiente. Disponible: {billetera.saldo}, requerido: {monto}."
            )
        billetera.saldo -= monto
        billetera.save(update_fields=["saldo"])

    MovimientoCaja.objects.create(
        usuario=conductor,
        monto=monto,
        tipo="egreso",
        descripcion=descripcion,
    )

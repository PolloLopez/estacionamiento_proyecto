# app_estacionamiento/use_cases/cobrar_estacionamiento.py
from decimal import Decimal

from app_estacionamiento.services.caja import registrar_cobro_efectivo


def ejecutar(inspector, monto, descripcion="", comision_monto=Decimal("0")):
    """
    Registra un cobro en la caja del inspector o vendedor.
    Delega en services/caja.py::registrar_cobro_efectivo().

    comision_monto: porción del monto que retiene el cobrador (calculada en la vista).
    """
    movimiento = registrar_cobro_efectivo(
        cobrador=inspector,
        monto=Decimal(monto),
        descripcion=descripcion,
        comision_monto=Decimal(comision_monto),
    )
    return {
        "ok": True,
        "movimiento": movimiento,
    }
